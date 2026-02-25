#!/usr/bin/env python3
"""
=============================================================================
FORESTGUARD - CRUCE DE INCENDIOS CON ÁREAS PROTEGIDAS
=============================================================================

Calcula las intersecciones espaciales entre fire_events y protected_areas,
almacenando los resultados en fire_protected_area_intersections.

Este es el paso crítico para el cálculo de prohibiciones legales según
la Ley 26.815 Art. 22 bis.

Modos de ejecución:
-------------------
1. BATCH (--mode batch): Procesa TODOS los fire_events
   - Usar para carga inicial o reprocessamiento completo
   - Puede tardar varios minutos dependiendo del volumen de datos

2. INCREMENTAL (--mode incremental): Solo fire_events sin procesar
   - Usa el flag has_legal_analysis=False para identificar pendientes
   - Ideal para ejecución diaria vía cron

Algoritmo:
----------
Para cada fire_event:
    1. Buscar protected_areas que intersecten con el centroid (ST_DWithin)
    2. Para cada intersección encontrada:
        - Calcular geometría de intersección (opcional)
        - Calcular área afectada en hectáreas
        - Calcular prohibition_until = fire_date + prohibition_years
    3. Marcar fire_event.has_legal_analysis = True

Uso:
----
    # Batch completo (primera vez)
    python scripts/cross_fire_protected_areas.py --mode batch
    
    # Incremental (diario)
    python scripts/cross_fire_protected_areas.py --mode incremental
    
    # Con opciones
    python scripts/cross_fire_protected_areas.py --mode batch --batch-size 1000
    python scripts/cross_fire_protected_areas.py --mode incremental --dry-run

Requisitos:
-----------
    pip install sqlalchemy geoalchemy2 psycopg2-binary python-dotenv

Autor: ForestGuard Team
Fecha: 2025-01
=============================================================================
"""

import argparse
import logging
import os
import sys
from datetime import date, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import create_engine, text, func, and_
from sqlalchemy.orm import sessionmaker, Session

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

def get_database_url() -> str:
    """Obtiene la URL de la base de datos desde variables de entorno."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    # Construir desde componentes (Supabase)
    db_host = os.getenv("SUPABASE_DB_HOST") or os.getenv("DB_HOST")
    db_port = os.getenv("SUPABASE_DB_PORT") or os.getenv("DB_PORT", "5432")
    db_name = os.getenv("SUPABASE_DB_NAME") or os.getenv("DB_NAME")
    db_user = os.getenv("SUPABASE_DB_USER") or os.getenv("DB_USER")
    db_password = os.getenv("SUPABASE_DB_PASSWORD") or os.getenv("DB_PASSWORD")
    
    if all([db_host, db_name, db_user, db_password]):
        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url
    
    raise ValueError("No se encontró configuración de base de datos.")


# =============================================================================
# FUNCIONES DE CRUCE ESPACIAL
# =============================================================================

def get_pending_fire_events(session: Session, mode: str, limit: Optional[int] = None) -> List[dict]:
    """
    Obtiene los fire_events pendientes de procesar.
    
    Args:
        session: Sesión de SQLAlchemy
        mode: 'batch' (todos) o 'incremental' (solo sin procesar)
        limit: Límite de registros (opcional)
    
    Returns:
        Lista de diccionarios con id, centroid, start_date
    """
    if mode == "batch":
        # Todos los fire_events
        query = text("""
            SELECT 
                id,
                ST_AsText(centroid) as centroid_wkt,
                start_date
            FROM fire_events
            ORDER BY start_date DESC
            LIMIT :limit
        """)
    else:
        # Solo los que no han sido procesados
        query = text("""
            SELECT 
                id,
                ST_AsText(centroid) as centroid_wkt,
                start_date
            FROM fire_events
            WHERE has_legal_analysis = FALSE OR has_legal_analysis IS NULL
            ORDER BY start_date DESC
            LIMIT :limit
        """)
    
    result = session.execute(query, {"limit": limit or 1000000})
    
    fire_events = []
    for row in result:
        fire_events.append({
            "id": row.id,
            "centroid_wkt": row.centroid_wkt,
            "start_date": row.start_date
        })
    
    return fire_events


def find_intersecting_protected_areas(
    session: Session,
    fire_event_id: str,
    centroid_wkt: str,
    buffer_meters: int = 5000
) -> List[dict]:
    """
    Encuentra áreas protegidas que intersectan con un fire_event.
    
    Usa ST_DWithin para búsqueda eficiente con índice GIST.
    El buffer de 5km captura incendios cercanos a los límites.
    
    Args:
        session: Sesión de SQLAlchemy
        fire_event_id: UUID del evento de incendio
        centroid_wkt: Centroid del incendio en WKT
        buffer_meters: Radio de búsqueda en metros
    
    Returns:
        Lista de áreas protegidas que intersectan
    """
    query = text("""
        SELECT 
            pa.id as protected_area_id,
            pa.official_name,
            pa.category,
            pa.prohibition_years,
            -- Verificar si el centroid está DENTRO del área (no solo cerca)
            ST_Intersects(
                pa.boundary::geometry,
                ST_SetSRID(ST_GeomFromText(:centroid_wkt), 4326)
            ) as is_inside,
            -- Distancia al borde más cercano
            ST_Distance(
                pa.boundary::geography,
                ST_SetSRID(ST_GeomFromText(:centroid_wkt), 4326)::geography
            ) as distance_meters
        FROM protected_areas pa
        WHERE ST_DWithin(
            pa.boundary::geography,
            ST_SetSRID(ST_GeomFromText(:centroid_wkt), 4326)::geography,
            :buffer_meters
        )
        ORDER BY distance_meters ASC
    """)
    
    result = session.execute(query, {
        "centroid_wkt": centroid_wkt,
        "buffer_meters": buffer_meters
    })
    
    areas = []
    for row in result:
        areas.append({
            "protected_area_id": row.protected_area_id,
            "official_name": row.official_name,
            "category": row.category,
            "prohibition_years": row.prohibition_years,
            "is_inside": row.is_inside,
            "distance_meters": row.distance_meters
        })
    
    return areas


def create_intersection_record(
    session: Session,
    fire_event_id: str,
    protected_area_id: str,
    fire_date: date,
    prohibition_years: int,
    distance_meters: float,
    is_inside: bool
) -> bool:
    """
    Crea un registro en fire_protected_area_intersections.
    
    Args:
        session: Sesión de SQLAlchemy
        fire_event_id: UUID del incendio
        protected_area_id: UUID del área protegida
        fire_date: Fecha del incendio
        prohibition_years: Años de prohibición (60 o 30)
        distance_meters: Distancia al área protegida
        is_inside: Si el centroid está dentro del área
    
    Returns:
        True si se insertó correctamente
    """
    # Calcular fecha de fin de prohibición
    prohibition_until = fire_date + timedelta(days=prohibition_years * 365)
    
    # Solo crear intersección si está DENTRO del área protegida
    # o muy cerca (< 100m) para capturar errores de georeferenciación
    if not is_inside and distance_meters > 100:
        return False
    
    query = text("""
        INSERT INTO fire_protected_area_intersections (
            id,
            fire_event_id,
            protected_area_id,
            fire_date,
            prohibition_until,
            overlap_percentage,
            created_at,
            updated_at
        ) VALUES (
            gen_random_uuid(),
            :fire_event_id,
            :protected_area_id,
            :fire_date,
            :prohibition_until,
            :overlap_percentage,
            NOW(),
            NOW()
        )
        ON CONFLICT (fire_event_id, protected_area_id) DO UPDATE SET
            prohibition_until = EXCLUDED.prohibition_until,
            updated_at = NOW()
    """)
    
    try:
        session.execute(query, {
            "fire_event_id": fire_event_id,
            "protected_area_id": protected_area_id,
            "fire_date": fire_date,
            "prohibition_until": prohibition_until,
            "overlap_percentage": 100.0 if is_inside else 50.0  # Simplificado
        })
        return True
    except Exception as e:
        logger.warning(f"Error creando intersección: {e}")
        return False


def mark_fire_event_processed(session: Session, fire_event_id: str):
    """Marca un fire_event como procesado."""
    query = text("""
        UPDATE fire_events 
        SET has_legal_analysis = TRUE,
            updated_at = NOW()
        WHERE id = :fire_event_id
    """)
    session.execute(query, {"fire_event_id": fire_event_id})


def clear_existing_intersections(session: Session, mode: str):
    """
    Limpia intersecciones existentes (solo en modo batch).
    
    Args:
        session: Sesión de SQLAlchemy
        mode: 'batch' para limpiar todo
    """
    if mode == "batch":
        logger.info("🗑️  Limpiando intersecciones existentes...")
        session.execute(text("DELETE FROM fire_protected_area_intersections"))
        session.execute(text("UPDATE fire_events SET has_legal_analysis = FALSE"))
        session.commit()
        logger.info("   Intersecciones eliminadas")


# =============================================================================
# FUNCIÓN PRINCIPAL DE CRUCE
# =============================================================================

def process_fire_events(
    session: Session,
    mode: str,
    batch_size: int = 500,
    dry_run: bool = False
) -> Tuple[int, int, int]:
    """
    Procesa los fire_events y crea intersecciones con áreas protegidas.
    
    Args:
        session: Sesión de SQLAlchemy
        mode: 'batch' o 'incremental'
        batch_size: Tamaño del lote para commits
        dry_run: Si True, no hace cambios en la BD
    
    Returns:
        Tuple (procesados, con_intersección, total_intersecciones)
    """
    # Obtener fire_events pendientes
    logger.info(f"🔍 Buscando fire_events ({mode})...")
    fire_events = get_pending_fire_events(session, mode)
    
    total = len(fire_events)
    if total == 0:
        logger.info("✅ No hay fire_events pendientes de procesar")
        return 0, 0, 0
    
    logger.info(f"   Encontrados: {total} fire_events")
    
    # Contadores
    processed = 0
    with_intersection = 0
    total_intersections = 0
    
    # Procesar cada fire_event
    for i, fe in enumerate(fire_events):
        fire_event_id = str(fe["id"])
        centroid_wkt = fe["centroid_wkt"]
        fire_date = fe["start_date"].date() if hasattr(fe["start_date"], 'date') else fe["start_date"]
        
        # Buscar áreas protegidas cercanas
        areas = find_intersecting_protected_areas(
            session,
            fire_event_id,
            centroid_wkt,
            buffer_meters=5000  # 5km de búsqueda
        )
        
        # Crear intersecciones
        intersections_created = 0
        for area in areas:
            if not dry_run:
                success = create_intersection_record(
                    session,
                    fire_event_id,
                    str(area["protected_area_id"]),
                    fire_date,
                    area["prohibition_years"],
                    area["distance_meters"],
                    area["is_inside"]
                )
                if success:
                    intersections_created += 1
            else:
                if area["is_inside"] or area["distance_meters"] <= 100:
                    intersections_created += 1
        
        # Marcar como procesado
        if not dry_run:
            mark_fire_event_processed(session, fire_event_id)
        
        # Actualizar contadores
        processed += 1
        if intersections_created > 0:
            with_intersection += 1
            total_intersections += intersections_created
        
        # Commit cada batch_size registros
        if processed % batch_size == 0:
            if not dry_run:
                session.commit()
            logger.info(f"   Progreso: {processed}/{total} ({with_intersection} con intersección)")
    
    # Commit final
    if not dry_run:
        session.commit()
    
    return processed, with_intersection, total_intersections


# =============================================================================
# ESTADÍSTICAS
# =============================================================================

def print_statistics(session: Session):
    """Imprime estadísticas del cruce."""
    
    # Total de intersecciones
    result = session.execute(text("""
        SELECT COUNT(*) as total FROM fire_protected_area_intersections
    """)).first()
    total_intersections = result.total
    
    # Intersecciones activas (prohibición vigente)
    result = session.execute(text("""
        SELECT COUNT(*) as active 
        FROM fire_protected_area_intersections
        WHERE prohibition_until > CURRENT_DATE
    """)).first()
    active_prohibitions = result.active
    
    # Fire events procesados
    result = session.execute(text("""
        SELECT 
            COUNT(*) FILTER (WHERE has_legal_analysis = TRUE) as processed,
            COUNT(*) as total
        FROM fire_events
    """)).first()
    
    # Top 5 áreas más afectadas
    top_areas = session.execute(text("""
        SELECT 
            pa.official_name,
            pa.category,
            COUNT(fpa.id) as fire_count
        FROM protected_areas pa
        JOIN fire_protected_area_intersections fpa ON fpa.protected_area_id = pa.id
        GROUP BY pa.id, pa.official_name, pa.category
        ORDER BY fire_count DESC
        LIMIT 5
    """)).fetchall()
    
    logger.info("\n" + "=" * 60)
    logger.info("📊 ESTADÍSTICAS DE CRUCE")
    logger.info("=" * 60)
    logger.info(f"   Fire events procesados: {result.processed}/{result.total}")
    logger.info(f"   Total intersecciones: {total_intersections}")
    logger.info(f"   Prohibiciones activas: {active_prohibitions}")
    
    if top_areas:
        logger.info("\n   🔥 Top 5 áreas más afectadas:")
        for area in top_areas:
            logger.info(f"      - {area.official_name} ({area.category}): {area.fire_count} incendios")
    
    logger.info("=" * 60)


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Cruza fire_events con protected_areas para calcular prohibiciones legales",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  %(prog)s --mode batch                    # Procesar todos (primera vez)
  %(prog)s --mode incremental              # Solo nuevos (diario)
  %(prog)s --mode batch --dry-run          # Simular sin cambios
  %(prog)s --mode incremental --batch-size 100
        """
    )
    
    parser.add_argument(
        "--mode",
        choices=["batch", "incremental"],
        required=True,
        help="Modo de ejecución: batch (todos) o incremental (nuevos)"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Registros por commit (default: 500)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simular sin hacer cambios en la BD"
    )
    
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="En modo batch, no limpiar intersecciones existentes"
    )
    
    args = parser.parse_args()
    
    # Banner
    logger.info("=" * 60)
    logger.info("🔥 FORESTGUARD - Cruce de Incendios con Áreas Protegidas")
    logger.info("=" * 60)
    logger.info(f"   Modo: {args.mode}")
    logger.info(f"   Batch size: {args.batch_size}")
    logger.info(f"   Dry-run: {args.dry_run}")
    logger.info("=" * 60)
    
    try:
        # Conectar a BD
        db_url = get_database_url()
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        # Asegurar columnas necesarias en esquema (compatibilidad con distintas versiones)
        def ensure_column(table: str, column: str, coldef: str):
            exists_q = text("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = :table AND column_name = :column)")
            exists = session.execute(exists_q, {"table": table, "column": column}).scalar()
            if not exists:
                logger.info(f"⚙️  Columna '{column}' ausente en '{table}', añadiendo...")
                try:
                    session.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {coldef}"))
                    session.commit()
                    logger.info(f"   Columna '{column}' añadida")
                except Exception as e:
                    logger.error(f"   No se pudo añadir columna '{column}': {e}")

        # Ensures
        ensure_column('fire_events', 'has_legal_analysis', 'boolean DEFAULT FALSE')
        logger.info("📊 Conectado a la base de datos")
        
        # Limpiar intersecciones existentes (solo batch sin --no-clear)
        if args.mode == "batch" and not args.no_clear and not args.dry_run:
            clear_existing_intersections(session, args.mode)
        
        # Procesar
        processed, with_intersection, total_intersections = process_fire_events(
            session,
            mode=args.mode,
            batch_size=args.batch_size,
            dry_run=args.dry_run
        )
        
        # Estadísticas
        if not args.dry_run:
            print_statistics(session)
        
        # Resumen final
        logger.info("\n" + "=" * 60)
        logger.info("✅ CRUCE COMPLETADO")
        logger.info(f"   Fire events procesados: {processed}")
        logger.info(f"   Con intersección en área protegida: {with_intersection}")
        logger.info(f"   Total intersecciones creadas: {total_intersections}")
        logger.info("=" * 60)
        
        session.close()
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
