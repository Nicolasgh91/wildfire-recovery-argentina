"""
Agrupa detecciones de incendios en eventos únicos usando clustering espacial.
VERSIÓN OPTIMIZADA CON MULTIPROCESSING.

Mejoras vs versión anterior:
- Paralelización por día usando ProcessPoolExecutor
- Batch inserts para reducir roundtrips a DB
- Chunking de rangos de fechas para mejor distribución de carga
- Manejo robusto de errores por proceso

Uso:
    # Un solo día
    python scripts/cluster_fire_events.py --date 2024-08-15
    
    # Rango de fechas (paralelo)
    python scripts/cluster_fire_events.py --start-date 2015-01-01 --end-date 2025-01-01
    
    # Controlar paralelismo
    python scripts/cluster_fire_events.py --start-date 2015-01-01 --end-date 2025-01-01 --workers 8
"""

import argparse
import logging
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import List, Tuple, Optional
import multiprocessing as mp

import numpy as np
from sklearn.cluster import DBSCAN
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker, Session
from tqdm import tqdm
from dotenv import load_dotenv

# --- CONFIGURACIÓN DE ENTORNO ---
base_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(base_dir))
load_dotenv(dotenv_path=base_dir / ".env")

from app.models.fire import FireDetection, FireEvent

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constantes
EARTH_RADIUS_METERS = 6371000.0


# =============================================================================
# CONFIGURACIÓN DE BASE DE DATOS
# =============================================================================

def build_db_url() -> str | URL:
    """Construye la URL de conexión a la base de datos."""
    if os.getenv("DB_HOST") and os.getenv("DB_PASSWORD"):
        return URL.create(
            "postgresql",
            username=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", 5432)),
            database=os.getenv("DB_NAME", "postgres"),
        )
    
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url.replace("postgres://", "postgresql://", 1)
    
    raise ValueError("No se encontraron credenciales de base de datos.")


def get_engine():
    """Crea un engine de SQLAlchemy (singleton por proceso)."""
    return create_engine(
        build_db_url(),
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True  # Verificar conexiones antes de usar
    )


# =============================================================================
# FUNCIÓN DE CLUSTERING (EJECUTADA EN CADA PROCESO)
# =============================================================================

def cluster_single_date(
    target_date: date,
    eps_meters: float = 1000,
    min_samples: int = 2
) -> Tuple[date, int, int]:
    """
    Procesa un solo día. Esta función se ejecuta en procesos separados.
    
    IMPORTANTE: Cada proceso crea su propia conexión a DB porque
    las conexiones de SQLAlchemy NO son thread/process-safe.
    
    Args:
        target_date: Fecha a procesar
        eps_meters: Radio de clustering en metros
        min_samples: Mínimo de puntos para formar cluster
    
    Returns:
        Tuple (fecha, eventos_creados, detecciones_procesadas)
    """
    # Cada proceso necesita su propio engine y session
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 1. Obtener detecciones del día
        detections = session.query(FireDetection).filter(
            FireDetection.acquisition_date == target_date,
            FireDetection.is_processed == False,
            FireDetection.confidence_normalized >= 50
        ).all()
        
        if not detections:
            return (target_date, 0, 0)
        
        num_detections = len(detections)
        
        # 2. Preparar datos para clustering
        coords = np.array([
            [float(d.latitude), float(d.longitude)] 
            for d in detections
        ], dtype=np.float64)
        
        # 3. Convertir a radianes para Haversine
        coords_rad = np.radians(coords)
        eps_rad = eps_meters / EARTH_RADIUS_METERS
        
        # 4. DBSCAN con Haversine
        clustering = DBSCAN(
            eps=eps_rad,
            min_samples=min_samples,
            metric='haversine',
            algorithm='ball_tree',
            n_jobs=1  # Ya estamos en paralelo a nivel de proceso
        ).fit(coords_rad)
        
        labels = clustering.labels_
        unique_labels = set(labels) - {-1}  # Excluir ruido
        
        if not unique_labels:
            # Marcar como procesadas aunque no formen cluster
            for d in detections:
                d.is_processed = True
            session.commit()
            return (target_date, 0, num_detections)
        
        # 5. Crear eventos en batch
        events_data = []
        detection_updates = []
        
        for cluster_id in unique_labels:
            cluster_mask = (labels == cluster_id)
            cluster_indices = np.where(cluster_mask)[0]
            cluster_detections = [detections[i] for i in cluster_indices]
            
            if not cluster_detections:
                continue
            
            # Calcular estadísticas del cluster
            event_data = calculate_event_stats(cluster_detections, target_date)
            events_data.append(event_data)
            
            # Guardar índices para actualizar después
            detection_updates.append((cluster_detections, len(events_data) - 1))
        
        # 6. Insertar eventos con INSERT directo (más rápido que ORM)
        if events_data:
            event_ids = bulk_insert_events(session, events_data)
            
            # 7. Actualizar detecciones
            for cluster_detections, event_idx in detection_updates:
                event_id = event_ids[event_idx]
                for d in cluster_detections:
                    d.is_processed = True
                    d.fire_event_id = event_id
        
        # Marcar detecciones de ruido como procesadas
        for i, d in enumerate(detections):
            if labels[i] == -1:
                d.is_processed = True
        
        session.commit()
        return (target_date, len(events_data), num_detections)
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error en {target_date}: {e}")
        return (target_date, 0, 0)
    finally:
        session.close()
        engine.dispose()  # Liberar conexiones del pool


def calculate_event_stats(detections: List[FireDetection], ref_date: date) -> dict:
    """Calcula estadísticas para un cluster de detecciones."""
    
    # Coordenadas
    lats = [float(d.latitude) for d in detections]
    lons = [float(d.longitude) for d in detections]
    avg_lat = sum(lats) / len(lats)
    avg_lon = sum(lons) / len(lons)
    
    # Fechas: priorizar detected_at (timestamp canónico), fallback a acquisition_date.
    valid_datetimes = [d.detected_at for d in detections if d.detected_at]
    if valid_datetimes:
        start_date = min(valid_datetimes)
        end_date = max(valid_datetimes)
    else:
        valid_dates = [d.acquisition_date for d in detections if d.acquisition_date]
        if valid_dates:
            start_date = datetime.combine(min(valid_dates), time.min, tzinfo=timezone.utc)
            end_date = datetime.combine(max(valid_dates), time.min, tzinfo=timezone.utc)
        else:
            start_date = datetime.combine(ref_date, time.min, tzinfo=timezone.utc)
            end_date = start_date
    
    # FRP (Fire Radiative Power)
    frp_values = [
        float(d.fire_radiative_power) 
        for d in detections 
        if d.fire_radiative_power is not None
    ]
    avg_frp = sum(frp_values) / len(frp_values) if frp_values else 0
    max_frp = max(frp_values) if frp_values else 0
    sum_frp = sum(frp_values) if frp_values else 0
    
    # Confianza
    conf_values = [
        d.confidence_normalized 
        for d in detections 
        if d.confidence_normalized is not None
    ]
    avg_conf = sum(conf_values) / len(conf_values) if conf_values else 0
    
    return {
        "centroid_wkt": f"POINT({avg_lon} {avg_lat})",
        "start_date": start_date,
        "end_date": end_date,
        "last_seen_at": end_date,
        "total_detections": len(detections),
        "avg_frp": round(avg_frp, 2),
        "max_frp": round(max_frp, 2),
        "sum_frp": round(sum_frp, 2),
        "avg_confidence": round(avg_conf, 2),
        "is_significant": (max_frp > 50 or avg_conf > 80),
    }


def bulk_insert_events(session: Session, events_data: List[dict]) -> List[str]:
    """
    Inserta eventos en batch usando SQL directo.
    Más rápido que el ORM para inserciones masivas.
    
    Returns:
        Lista de UUIDs generados
    """
    if not events_data:
        return []
    
    # Usar INSERT con RETURNING para obtener IDs
    query = text("""
        INSERT INTO fire_events (
            id, centroid, start_date, end_date, last_seen_at,
            total_detections, avg_frp, max_frp, sum_frp,
            avg_confidence, is_significant, has_legal_analysis,
            created_at, updated_at
        ) VALUES (
            gen_random_uuid(),
            ST_GeomFromText(:centroid_wkt, 4326)::geography,
            :start_date, :end_date, :last_seen_at,
            :total_detections, :avg_frp, :max_frp, :sum_frp,
            :avg_confidence, :is_significant, FALSE,
            NOW(), NOW()
        )
        RETURNING id
    """)
    
    event_ids = []
    for data in events_data:
        result = session.execute(query, data)
        event_id = result.fetchone()[0]
        event_ids.append(event_id)
    
    return event_ids


# =============================================================================
# ORQUESTADOR DE PARALELISMO
# =============================================================================

def cluster_date_range_parallel(
    start_date: date,
    end_date: date,
    eps_meters: float = 1000,
    min_samples: int = 2,
    max_workers: Optional[int] = None
) -> Tuple[int, int]:
    """
    Procesa un rango de fechas en paralelo.
    
    Args:
        start_date: Fecha inicial
        end_date: Fecha final
        eps_meters: Radio de clustering
        min_samples: Mínimo puntos por cluster
        max_workers: Número de procesos (None = CPUs disponibles)
    
    Returns:
        Tuple (total_eventos, total_detecciones)
    """
    # Generar lista de fechas
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    
    total_days = len(dates)
    
    # Determinar número de workers
    if max_workers is None:
        max_workers = min(mp.cpu_count(), 8)  # Máximo 8 para no saturar DB
    
    logger.info(f"🚀 Iniciando clustering paralelo")
    logger.info(f"   Rango: {start_date} → {end_date} ({total_days} días)")
    logger.info(f"   Workers: {max_workers}")
    logger.info(f"   Parámetros: eps={eps_meters}m, min_samples={min_samples}")
    
    total_events = 0
    total_detections = 0
    errors = 0
    
    # ProcessPoolExecutor para CPU-bound tasks
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Enviar todas las tareas
        futures = {
            executor.submit(
                cluster_single_date, 
                d, 
                eps_meters, 
                min_samples
            ): d 
            for d in dates
        }
        
        # Procesar resultados con barra de progreso
        with tqdm(total=total_days, desc="Procesando", unit="día") as pbar:
            for future in as_completed(futures):
                target_date = futures[future]
                try:
                    result_date, events, detections = future.result()
                    total_events += events
                    total_detections += detections
                    
                    # Actualizar descripción con stats
                    if events > 0:
                        pbar.set_postfix({
                            "eventos": total_events,
                            "último": f"{events} en {result_date}"
                        })
                        
                except Exception as e:
                    logger.error(f"Error procesando {target_date}: {e}")
                    errors += 1
                
                pbar.update(1)
    
    logger.info(f"✅ COMPLETADO")
    logger.info(f"   Total eventos: {total_events}")
    logger.info(f"   Total detecciones procesadas: {total_detections}")
    if errors > 0:
        logger.warning(f"   Errores: {errors}")
    
    return total_events, total_detections


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Clustering de incendios con DBSCAN Haversine (Paralelo)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  %(prog)s --date 2024-08-15                    # Un solo día
  %(prog)s --start-date 2020-01-01 --end-date 2024-12-31  # Rango paralelo
  %(prog)s --start-date 2020-01-01 --end-date 2024-12-31 --workers 4
        """
    )
    
    parser.add_argument(
        '--date',
        type=lambda s: datetime.strptime(s, '%Y-%m-%d').date(),
        help='Fecha específica a procesar'
    )
    parser.add_argument(
        '--start-date',
        type=lambda s: datetime.strptime(s, '%Y-%m-%d').date(),
        help='Fecha inicial del rango'
    )
    parser.add_argument(
        '--end-date',
        type=lambda s: datetime.strptime(s, '%Y-%m-%d').date(),
        help='Fecha final del rango'
    )
    parser.add_argument(
        '--eps-meters',
        type=float,
        default=1000,
        help='Radio de clustering en metros (default: 1000)'
    )
    parser.add_argument(
        '--min-samples',
        type=int,
        default=2,
        help='Mínimo puntos para formar cluster (default: 2)'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=None,
        help='Número de procesos paralelos (default: CPUs disponibles, max 8)'
    )
    
    args = parser.parse_args()
    
    if args.date:
        # Modo single-day (sin paralelismo)
        logger.info(f"📅 Procesando fecha única: {args.date}")
        result = cluster_single_date(
            args.date,
            eps_meters=args.eps_meters,
            min_samples=args.min_samples
        )
        logger.info(f"✅ Resultado: {result[1]} eventos de {result[2]} detecciones")
        
    elif args.start_date and args.end_date:
        # Modo rango (paralelo)
        cluster_date_range_parallel(
            args.start_date,
            args.end_date,
            eps_meters=args.eps_meters,
            min_samples=args.min_samples,
            max_workers=args.workers
        )
    else:
        parser.print_help()
        print("\n⚠️  Debes especificar --date O --start-date y --end-date")
        sys.exit(1)


if __name__ == '__main__':
    # Necesario para multiprocessing en Windows
    mp.freeze_support()
    main()
