#!/usr/bin/env python3
"""
=============================================================================
FORESTGUARD - CARGA INCREMENTAL DIARIA DE NASA FIRMS
=============================================================================

Descarga y procesa los datos de incendios de las últimas 24-48 horas desde
la API de NASA FIRMS, ejecuta el clustering y el cruce con áreas protegidas.

Diseñado para ejecutarse como cron job diario.

Pipeline completo:
1. Descargar datos recientes de FIRMS (últimas 24-48h)
2. Filtrar por Argentina y confianza
3. Insertar en fire_detections (evitando duplicados)
4. Ejecutar clustering en las fechas nuevas
5. Calcular áreas de los nuevos eventos
6. Ejecutar cruce incremental con áreas protegidas

Configuración cron (ejecutar a las 6 AM):
    0 6 * * * /path/to/venv/bin/python /path/to/scripts/load_firms_incremental.py

Requisitos:
    - Variable de entorno FIRMS_API_KEY (obtener en https://firms.modaps.eosdis.nasa.gov/api/)
    - Acceso a la base de datos configurado en .env

Uso manual:
    python scripts/load_firms_incremental.py
    python scripts/load_firms_incremental.py --days 3  # Últimos 3 días
    python scripts/load_firms_incremental.py --dry-run  # Solo mostrar, no insertar

Autor: ForestGuard Team
Fecha: 2025-01
=============================================================================
"""

import argparse
import csv
import io
import logging
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import List, Tuple, Optional
import hashlib

import requests
from sqlalchemy import bindparam, create_engine, text
from sqlalchemy.engine import URL
from dotenv import load_dotenv

# --- CONFIGURACIÓN ---
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
load_dotenv(dotenv_path=BASE_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(BASE_DIR / "logs" / "firms_incremental.log", mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Crear directorio de logs si no existe
(BASE_DIR / "logs").mkdir(exist_ok=True)

# Constantes
FIRMS_API_BASE = "https://firms.modaps.eosdis.nasa.gov/api/country/csv"
ARGENTINA_CODE = "ARG"
SATELLITES = ["VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT"]

# Bounding box de Argentina (para filtrado adicional)
ARG_BOUNDS = {
    "lat_min": -56.0,
    "lat_max": -21.0,
    "lon_min": -74.0,
    "lon_max": -53.0
}

DEFAULT_H3_RESOLUTION = 8

try:
    import h3  # type: ignore
    H3_AVAILABLE = True
except ImportError:
    h3 = None
    H3_AVAILABLE = False


def resolve_h3_resolution(engine=None) -> int:
    """Resolve H3 resolution from env/system_parameters, fallback to default."""
    env_value = os.getenv("H3_RESOLUTION")
    if env_value:
        try:
            return int(env_value)
        except (TypeError, ValueError):
            logger.warning("H3_RESOLUTION inválido: %s", env_value)

    if engine is None:
        return DEFAULT_H3_RESOLUTION

    try:
        with engine.connect() as conn:
            row = (
                conn.execute(
                    text("SELECT param_value FROM system_parameters WHERE param_key = 'h3_resolution'")
                )
                .mappings()
                .first()
            )
        if not row:
            return DEFAULT_H3_RESOLUTION
        value = row.get("param_value")
        if isinstance(value, dict):
            value = value.get("value")
        if isinstance(value, (int, float, str)):
            return int(value)
    except Exception as exc:
        logger.warning("No se pudo leer system_parameters.h3_resolution: %s", exc)

    return DEFAULT_H3_RESOLUTION


def get_fire_detection_columns(engine) -> set[str]:
    query = text(
        """
        SELECT column_name
          FROM information_schema.columns
         WHERE table_schema = 'public'
           AND table_name = 'fire_detections'
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(query).fetchall()
    return {row[0] for row in rows}


def normalize_acquisition_time(raw_value: Optional[str]) -> tuple[str, int, int]:
    """Normalize FIRMS acq_time to HH:MM:SS and return (time_str, hour, minute)."""
    raw = "" if raw_value is None else str(raw_value)
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        digits = "0000"
    digits = digits.zfill(4)
    if len(digits) > 4:
        digits = digits[-4:]
    hour = int(digits[:2])
    minute = int(digits[2:4])
    return f"{hour:02d}:{minute:02d}:00", hour, minute


def build_detected_at(acq_date_raw: str, acq_time_raw: Optional[str]) -> tuple[date, str, datetime]:
    acq_date = datetime.strptime(acq_date_raw, "%Y-%m-%d").date()
    time_str, hour, minute = normalize_acquisition_time(acq_time_raw)
    detected_at = datetime(
        acq_date.year,
        acq_date.month,
        acq_date.day,
        hour,
        minute,
        tzinfo=timezone.utc,
    )
    return acq_date, time_str, detected_at


def build_detection_hash(
    *,
    satellite: str,
    instrument: str,
    detected_at: datetime,
    lat: float,
    lon: float,
    frp: float,
    confidence: int,
) -> str:
    payload = "|".join(
        [
            satellite,
            instrument,
            detected_at.astimezone(timezone.utc).isoformat(),
            f"{lat:.5f}",
            f"{lon:.5f}",
            f"{frp:.2f}",
            str(confidence),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compute_h3_index(lat: float, lon: float, resolution: int) -> int:
    if not H3_AVAILABLE:
        raise RuntimeError("h3 library no disponible; instala el paquete 'h3'")
    if hasattr(h3, "latlng_to_cell"):
        h3_str = h3.latlng_to_cell(lat, lon, resolution)
    else:
        h3_str = h3.geo_to_h3(lat, lon, resolution)
    return int(h3_str, 16)


# =============================================================================
# BASE DE DATOS
# =============================================================================

def get_db_url() -> str | URL:
    """Construye URL de conexión."""
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
    
    raise ValueError("No se encontraron credenciales de base de datos")


def get_engine():
    """Crea engine de SQLAlchemy."""
    return create_engine(get_db_url(), pool_pre_ping=True)


# =============================================================================
# DESCARGA DE FIRMS
# =============================================================================

def download_firms_data(
    api_key: str,
    satellite: str,
    days: int = 2
) -> List[dict]:
    """
    Descarga datos de FIRMS para Argentina.
    
    Args:
        api_key: API key de NASA FIRMS
        satellite: Satélite (VIIRS_SNPP_NRT, VIIRS_NOAA20_NRT, etc.)
        days: Número de días hacia atrás (1-10)
    
    Returns:
        Lista de diccionarios con las detecciones
    """
    url = f"{FIRMS_API_BASE}/{api_key}/{satellite}/{ARGENTINA_CODE}/{days}"
    
    logger.info(f" Descargando {satellite} (últimos {days} días)...")
    
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        
        # Parsear CSV
        reader = csv.DictReader(io.StringIO(response.text))
        detections = list(reader)
        
        logger.info(f"   Recibidos: {len(detections)} registros")
        return detections
        
    except requests.exceptions.RequestException as e:
        logger.error(f"   Error descargando {satellite}: {e}")
        return []


def normalize_confidence(raw_value: str, satellite: str) -> int:
    """
    Normaliza el valor de confianza a escala 0-100.
    
    VIIRS usa valores numéricos directos (0-100).
    MODIS usa letras: l=33, n=66, h=100.
    """
    if not raw_value:
        return 0
    
    raw_lower = raw_value.lower().strip()
    
    # MODIS usa letras
    if raw_lower in ('l', 'low'):
        return 33
    elif raw_lower in ('n', 'nominal'):
        return 66
    elif raw_lower in ('h', 'high'):
        return 100
    
    # VIIRS usa números
    try:
        val = int(float(raw_value))
        return max(0, min(100, val))
    except (ValueError, TypeError):
        return 0


def filter_and_transform(
    detections: List[dict],
    satellite: str,
    *,
    compute_h3: bool,
    h3_resolution: int,
) -> List[dict]:
    """
    Filtra y transforma las detecciones.

    Filtros:
    - Dentro del bounding box de Argentina
    - Confianza >= 50%

    Transformaciones:
    - Normalizar confianza
    - Parsear fechas
    - Generar hash ?nico para detecci?n de duplicados
    """
    filtered = []

    for det in detections:
        try:
            lat = float(det.get("latitude", 0))
            lon = float(det.get("longitude", 0))

            # Filtrar por bounding box
            if not (ARG_BOUNDS["lat_min"] <= lat <= ARG_BOUNDS["lat_max"]):
                continue
            if not (ARG_BOUNDS["lon_min"] <= lon <= ARG_BOUNDS["lon_max"]):
                continue

            # Normalizar confianza
            confidence = normalize_confidence(det.get("confidence", "0"), satellite)

            # Filtrar baja confianza
            if confidence < 50:
                continue

            # Parsear fecha
            acq_date_raw = det.get("acq_date", "")
            acq_time_raw = det.get("acq_time", "0000")

            if not acq_date_raw:
                continue

            acq_date, acq_time, detected_at = build_detected_at(acq_date_raw, acq_time_raw)
            sat_name = satellite.replace("_NRT", "").replace("_", "-")
            instrument = "VIIRS" if "VIIRS" in satellite else "MODIS"
            frp = float(det.get("frp", 0) or 0)

            detection_hash = build_detection_hash(
                satellite=sat_name,
                instrument=instrument,
                detected_at=detected_at,
                lat=lat,
                lon=lon,
                frp=frp,
                confidence=confidence,
            )

            legacy_str = f"{lat:.5f}|{lon:.5f}|{acq_date.isoformat()}|{acq_time}|{sat_name}"
            legacy_hash = hashlib.md5(legacy_str.encode()).hexdigest()[:16]

            payload = {
                "satellite": sat_name,
                "instrument": instrument,
                "detected_at": detected_at,
                "latitude": lat,
                "longitude": lon,
                "acquisition_date": acq_date,
                "acquisition_time": acq_time,
                "confidence_raw": det.get("confidence", ""),
                "confidence_normalized": confidence,
                "fire_radiative_power": frp,
                "bright_ti4": float(det.get("bright_ti4", 0) or 0),
                "bright_ti5": float(det.get("bright_ti5", 0) or 0),
                "daynight": det.get("daynight", "D"),
                "detection_hash": detection_hash,
                "legacy_hash": legacy_hash,
            }

            if compute_h3:
                payload["h3_index"] = compute_h3_index(lat, lon, h3_resolution)

            filtered.append(payload)

        except (ValueError, TypeError):
            continue

    return filtered


# =============================================================================
# INSERCIÓN EN BASE DE DATOS
# =============================================================================

def get_existing_hashes(engine, acq_dates: List[date], use_detection_hash: bool) -> set[str]:
    """
    Obtiene los hashes de detecciones existentes para las fechas dadas.
    Esto permite evitar duplicados eficientemente.
    """
    if not acq_dates:
        return set()

    if use_detection_hash:
        query = text(
            """
            SELECT detection_hash
              FROM fire_detections
             WHERE acquisition_date IN :dates
               AND detection_hash IS NOT NULL
            """
        ).bindparams(bindparam("dates", expanding=True))
        with engine.connect() as conn:
            result = conn.execute(query, {"dates": acq_dates}).fetchall()
        return {row[0] for row in result if row[0]}

    query = text(
        """
        SELECT DISTINCT 
            MD5(
                ROUND(latitude::numeric, 5)::text || '|' ||
                ROUND(longitude::numeric, 5)::text || '|' ||
                acquisition_date::text || '|' ||
                COALESCE(acquisition_time::text, '00:00:00') || '|' ||
                satellite
            )::varchar(16) as hash
        FROM fire_detections
        WHERE acquisition_date IN :dates
        """
    ).bindparams(bindparam("dates", expanding=True))

    with engine.connect() as conn:
        result = conn.execute(query, {"dates": acq_dates}).fetchall()
    return {row[0] for row in result if row[0]}


def insert_detections(
    engine,
    detections: List[dict],
    dry_run: bool = False,
    *,
    supports_detection_hash: bool,
    supports_h3: bool,
    supports_created_at: bool,
) -> dict:
    """
    Inserta detecciones nuevas en la base de datos.

    Args:
        engine: SQLAlchemy engine
        detections: Lista de detecciones a insertar
        dry_run: Si True, solo simula sin insertar

    Returns:
        N?mero de detecciones insertadas
    """
    if not detections:
        return {"inserted": 0, "duplicates": 0, "attempted": 0, "skipped_errors": 0}

    # Obtener fechas ?nicas
    unique_dates = list(set(d["acquisition_date"] for d in detections))

    # Obtener hashes existentes
    existing_hashes = get_existing_hashes(engine, unique_dates, supports_detection_hash)
    logger.info(f"   Hashes existentes para estas fechas: {len(existing_hashes)}")

    # Filtrar duplicados
    if supports_detection_hash:
        new_detections = [d for d in detections if d["detection_hash"] not in existing_hashes]
    else:
        new_detections = [d for d in detections if d["legacy_hash"] not in existing_hashes]

    duplicates = len(detections) - len(new_detections)
    logger.info(f"   Detecciones nuevas: {len(new_detections)} de {len(detections)}")

    if dry_run or not new_detections:
        return {
            "inserted": len(new_detections),
            "duplicates": duplicates,
            "attempted": len(detections),
            "skipped_errors": 0,
        }

    columns = [
        "id",
        "satellite",
        "instrument",
        "detected_at",
        "latitude",
        "longitude",
        "location",
        "acquisition_date",
        "acquisition_time",
        "confidence_raw",
        "confidence_normalized",
        "fire_radiative_power",
        "bt_mir_kelvin",
        "bt_tir_kelvin",
        "daynight",
        "is_processed",
        "fire_event_id",
    ]
    values = [
        "gen_random_uuid()",
        ":satellite",
        ":instrument",
        ":detected_at",
        ":latitude",
        ":longitude",
        "ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography",
        ":acquisition_date",
        ":acquisition_time",
        ":confidence_raw",
        ":confidence_normalized",
        ":fire_radiative_power",
        ":bright_ti4",
        ":bright_ti5",
        ":daynight",
        "FALSE",
        "NULL",
    ]

    if supports_h3:
        columns.append("h3_index")
        values.append(":h3_index")
    if supports_detection_hash:
        columns.append("detection_hash")
        values.append(":detection_hash")
    if supports_created_at:
        columns.append("created_at")
        values.append("NOW()")

    insert_sql = text(
        f"""
        INSERT INTO fire_detections (
            {', '.join(columns)}
        ) VALUES (
            {', '.join(values)}
        )
        """
    )

    inserted = 0
    batch_size = 1000

    with engine.begin() as conn:
        for i in range(0, len(new_detections), batch_size):
            batch = new_detections[i:i + batch_size]
            for det in batch:
                try:
                    payload = {
                        "satellite": det["satellite"],
                        "instrument": det["instrument"],
                        "detected_at": det["detected_at"],
                        "latitude": det["latitude"],
                        "longitude": det["longitude"],
                        "acquisition_date": det["acquisition_date"],
                        "acquisition_time": det["acquisition_time"],
                        "confidence_raw": det["confidence_raw"],
                        "confidence_normalized": det["confidence_normalized"],
                        "fire_radiative_power": det["fire_radiative_power"],
                        "bright_ti4": det["bright_ti4"],
                        "bright_ti5": det["bright_ti5"],
                        "daynight": det["daynight"],
                    }
                    if supports_h3:
                        payload["h3_index"] = det.get("h3_index")
                    if supports_detection_hash:
                        payload["detection_hash"] = det.get("detection_hash")

                    conn.execute(insert_sql, payload)
                    inserted += 1
                except Exception as e:
                    logger.warning(f"Error insertando detecci?n: {e}")
                    continue

    skipped_errors = len(new_detections) - inserted
    return {
        "inserted": inserted,
        "duplicates": duplicates,
        "attempted": len(detections),
        "skipped_errors": skipped_errors,
    }


# =============================================================================
# POST-PROCESAMIENTO
# =============================================================================

def run_clustering_for_dates(engine, dates: List[date]) -> int:
    """
    Ejecuta clustering para las fechas especificadas usando el worker canónico.
    """
    if not dates:
        return 0

    from app.db.session import SessionLocal
    from app.services.detection_clustering_service import DetectionClusteringService

    min_date = min(dates)
    if isinstance(min_date, str):
        min_date = datetime.strptime(min_date, "%Y-%m-%d").date()
    days_back = max(1, (date.today() - min_date).days + 1)

    db = SessionLocal()
    try:
        logger.info(f"🔄 Ejecutando clustering (days_back={days_back})...")
        service = DetectionClusteringService(db)
        result = service.run_clustering(days_back=days_back)
        db.commit()
        events_created = int(result.get("events_created", 0))
        logger.info(f"   Eventos creados: {events_created}")
        return events_created
    except Exception as exc:
        db.rollback()
        logger.warning("   Clustering falló: %s", exc)
        raise
    finally:
        db.close()


def run_area_calculation(engine) -> int:
    """Calcula áreas para eventos sin área."""
    logger.info("📐 Calculando áreas de nuevos eventos...")
    
    sql = text("""
        WITH detection_stats AS (
            SELECT 
                fe.id as event_id,
                COUNT(fd.id) as det_count,
                ST_Collect(fd.location::geometry) as points_geom,
                ST_Centroid(ST_Collect(fd.location::geometry)) as centroid
            FROM fire_events fe
            JOIN fire_detections fd ON fd.fire_event_id = fe.id
            WHERE fe.estimated_area_hectares IS NULL
            GROUP BY fe.id
        ),
        calculated_areas AS (
            SELECT
                event_id,
                CASE
                    WHEN det_count = 1 THEN
                        ST_Buffer(centroid::geography, 375)::geometry
                    WHEN det_count = 2 THEN
                        ST_Buffer(ST_MakeLine(
                            ST_GeometryN(points_geom, 1),
                            ST_GeometryN(points_geom, 2)
                        )::geography, 200)::geometry
                    ELSE
                        CASE
                            WHEN GeometryType(ST_ConvexHull(points_geom)) = 'POLYGON' THEN
                                ST_ConvexHull(points_geom)
                            ELSE
                                ST_Buffer(centroid::geography, 375)::geometry
                        END
                END as calculated_geom
            FROM detection_stats
        )
        UPDATE fire_events fe
        SET
            perimeter = ST_SetSRID(ca.calculated_geom, 4326)::geography,
            estimated_area_hectares = ROUND(
                (ST_Area(ca.calculated_geom::geography) / 10000)::numeric, 2
            ),
            updated_at = NOW()
        FROM calculated_areas ca
        WHERE fe.id = ca.event_id
        RETURNING fe.id
    """)
    
    with engine.begin() as conn:
        result = conn.execute(sql)
        count = result.rowcount
    
    logger.info(f"   Áreas calculadas: {count}")
    return count


def run_legal_crossing(engine) -> int:
    """Ejecuta cruce incremental con áreas protegidas."""
    logger.info("⚖️ Ejecutando cruce legal incremental...")
    
    # Buscar eventos sin análisis legal
    sql = text("""
        WITH pending_events AS (
            SELECT 
                fe.id as fire_event_id,
                ST_AsText(fe.centroid) as centroid_wkt,
                fe.start_date
            FROM fire_events fe
            WHERE fe.has_legal_analysis = FALSE OR fe.has_legal_analysis IS NULL
        ),
        intersections AS (
            SELECT 
                pe.fire_event_id,
                pa.id as protected_area_id,
                pe.start_date as fire_date,
                pa.prohibition_years,
                ST_Intersects(pa.boundary::geometry, ST_GeomFromText(pe.centroid_wkt, 4326)) as is_inside
            FROM pending_events pe
            CROSS JOIN protected_areas pa
            WHERE ST_DWithin(
                pa.boundary::geography,
                ST_GeomFromText(pe.centroid_wkt, 4326)::geography,
                5000
            )
        )
        INSERT INTO fire_protected_area_intersections (
            id, fire_event_id, protected_area_id,
            fire_date, prohibition_until,
            overlap_percentage, created_at
        )
        SELECT 
            gen_random_uuid(),
            fire_event_id,
            protected_area_id,
            fire_date,
            fire_date + (prohibition_years * INTERVAL '1 year'),
            CASE WHEN is_inside THEN 100.0 ELSE 50.0 END,
            NOW()
        FROM intersections
        WHERE is_inside = TRUE
        ON CONFLICT (fire_event_id, protected_area_id) DO NOTHING
        RETURNING id
    """)
    
    with engine.begin() as conn:
        result = conn.execute(sql)
        intersections_created = result.rowcount
        
        # Marcar eventos como procesados
        conn.execute(text("""
            UPDATE fire_events 
            SET has_legal_analysis = TRUE, updated_at = NOW()
            WHERE has_legal_analysis = FALSE OR has_legal_analysis IS NULL
        """))
    
    logger.info(f"   Intersecciones creadas: {intersections_created}")
    return intersections_created


# =============================================================================
# PIPELINE PRINCIPAL
# =============================================================================

def run_incremental_pipeline(days: int = 2, dry_run: bool = False):
    """
    Ejecuta el pipeline completo de actualización incremental.
    
    Args:
        days: Días hacia atrás a consultar (1-10)
        dry_run: Si True, solo simula sin modificar la BD
    """
    logger.info("=" * 60)
    logger.info("INFO FORESTGUARD - Actualización Incremental FIRMS")
    logger.info("=" * 60)
    logger.info(f"   Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"   Días a consultar: {days}")
    logger.info(f"   Modo: {'DRY-RUN (simulación)' if dry_run else 'PRODUCCIÓN'}")
    logger.info("=" * 60)
    
    # Verificar API key
    api_key = os.getenv("FIRMS_API_KEY")
    if not api_key:
        raise RuntimeError("FIRMS_API_KEY no configurada")
    
    engine = get_engine()
    columns = get_fire_detection_columns(engine)
    supports_h3 = "h3_index" in columns
    supports_detection_hash = "detection_hash" in columns
    supports_created_at = "created_at" in columns
    h3_resolution = resolve_h3_resolution(engine)

    if supports_h3 and not H3_AVAILABLE:
        raise RuntimeError("h3_index existe pero la librería h3 no está instalada")
    
    # 1. Descargar datos de todos los satélites
    all_detections = []
    for satellite in SATELLITES:
        raw_data = download_firms_data(api_key, satellite, days)
        filtered = filter_and_transform(
            raw_data,
            satellite,
            compute_h3=supports_h3,
            h3_resolution=h3_resolution,
        )
        all_detections.extend(filtered)
    
    logger.info(f"\n Total detecciones filtradas: {len(all_detections)}")
    
    if not all_detections:
        logger.info(" No hay nuevos datos para procesar")
        return {
            "success": True,
            "records_inserted": 0,
            "duplicates_found": 0,
            "total_filtered": 0,
            "events_created": 0,
            "areas_calculated": 0,
            "intersections": 0,
        }
    
    # 2. Insertar en BD
    insert_result = insert_detections(
        engine,
        all_detections,
        dry_run,
        supports_detection_hash=supports_detection_hash,
        supports_h3=supports_h3,
        supports_created_at=supports_created_at,
    )
    inserted = int(insert_result.get("inserted", 0))
    duplicates = int(insert_result.get("duplicates", 0))
    skipped_errors = int(insert_result.get("skipped_errors", 0))
    logger.info(f" Detecciones insertadas: {inserted}")
    logger.info(f" Detecciones duplicadas: {duplicates}")
    if skipped_errors:
        logger.info(f" Detecciones con error de insert: {skipped_errors}")
    
    if dry_run or inserted == 0:
        logger.info(" Pipeline completado (dry-run o sin datos nuevos)")
        return {
            "success": True,
            "records_inserted": inserted,
            "duplicates_found": duplicates,
            "total_filtered": len(all_detections),
            "events_created": 0,
            "areas_calculated": 0,
            "intersections": 0,
        }
    
    # 3. Obtener fechas únicas para procesamiento
    unique_dates = list(set(d["acquisition_date"] for d in all_detections))
    
    # 4. Clustering
    events_created = run_clustering_for_dates(engine, unique_dates)
    
    # 5. Calcular áreas
    areas_calculated = run_area_calculation(engine)
    
    # 6. Cruce legal
    intersections = run_legal_crossing(engine)
    
    # Resumen final
    logger.info("\n" + "=" * 60)
    logger.info("✅ PIPELINE COMPLETADO")
    logger.info("=" * 60)
    logger.info(f"   Detecciones insertadas: {inserted}")
    logger.info(f"   Eventos creados: {events_created}")
    logger.info(f"   Áreas calculadas: {areas_calculated}")
    logger.info(f"   Intersecciones legales: {intersections}")
    logger.info("=" * 60)
    return {
        "success": True,
        "records_inserted": inserted,
        "duplicates_found": duplicates,
        "total_filtered": len(all_detections),
        "events_created": events_created,
        "areas_calculated": areas_calculated,
        "intersections": intersections,
    }


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Carga incremental diaria de datos FIRMS',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  %(prog)s                    # Últimos 2 días (default)
  %(prog)s --days 3           # Últimos 3 días
  %(prog)s --dry-run          # Simular sin insertar
  
Configuración cron (ejecutar diario a las 6 AM):
  0 6 * * * /path/to/venv/bin/python /path/to/scripts/load_firms_incremental.py >> /var/log/firms.log 2>&1
        """
    )
    
    parser.add_argument(
        '--days',
        type=int,
        default=2,
        choices=range(1, 11),
        metavar='N',
        help='Días hacia atrás a consultar (1-10, default: 2)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simular sin modificar la base de datos'
    )
    
    args = parser.parse_args()
    
    try:
        run_incremental_pipeline(days=args.days, dry_run=args.dry_run)
    except Exception as e:
        logger.error(f"❌ Error en pipeline: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
