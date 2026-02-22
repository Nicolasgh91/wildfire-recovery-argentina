"""
=============================================================================
FORESTGUARD - CÁLCULO DE ÁREAS DE INCENDIOS
=============================================================================

Calcula el perímetro (ConvexHull) y área en hectáreas para cada fire_event
basándose en las detecciones asociadas.

Casos manejados:
- 1-2 detecciones: Usa buffer circular (estimación)
- 3+ detecciones colineales: Usa buffer sobre la línea
- 3+ detecciones no colineales: ConvexHull real

El área se calcula en el sistema de coordenadas Geography (metros²)
y se convierte a hectáreas (÷ 10,000).

Uso:
    python scripts/calculate_area.py
    python scripts/calculate_area.py --batch-size 5000

Autor: ForestGuard Team
=============================================================================
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Setup
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
load_dotenv(dotenv_path=BASE_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_db_url() -> str:
    """Construye URL de conexión a la base de datos."""
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME", "postgres")
    
    if password and host:
        return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url.replace("postgres://", "postgresql://", 1)
    
    raise ValueError("No se encontraron credenciales de base de datos")


def calculate_fire_areas(batch_size: int = 10000):
    """
    Calcula perímetros y áreas para todos los fire_events.
    
    Estrategia:
    1. Para eventos con 1-2 detecciones: buffer circular de 375m (resolución VIIRS)
    2. Para eventos con 3+ detecciones: ConvexHull o buffer si son colineales
    3. Área calculada en Geography (precisión real en metros²)
    """
    logger.info("📐 Calculando perímetros y áreas de incendios...")
    
    engine = create_engine(get_db_url())
    
    # Primero, contar cuántos eventos hay que procesar
    with engine.connect() as conn:
        count_result = conn.execute(text("""
            SELECT COUNT(*) FROM fire_events 
            WHERE estimated_area_hectares IS NULL
        """))
        total_pending = count_result.scalar()
        logger.info(f"   Eventos pendientes: {total_pending}")
    
    if total_pending == 0:
        logger.info("✅ Todos los eventos ya tienen área calculada")
        return
    
    # SQL optimizado que maneja TODOS los casos edge
    sql = text("""
        WITH detection_stats AS (
            -- Contar detecciones y recolectar geometrías por evento
            SELECT 
                fe.id as event_id,
                COUNT(fd.id) as det_count,
                ST_Collect(fd.location::geometry) as points_geom,
                -- Centroide para casos de buffer
                ST_Centroid(ST_Collect(fd.location::geometry)) as centroid
            FROM fire_events fe
            JOIN fire_detections fd ON fd.fire_event_id = fe.id
            WHERE fe.estimated_area_hectares IS NULL
            GROUP BY fe.id
        ),
        calculated_areas AS (
            SELECT
                event_id,
                det_count,
                CASE
                    -- Caso 1: Solo 1 detección → buffer circular 375m (resolución VIIRS)
                    WHEN det_count = 1 THEN
                        ST_Buffer(centroid::geography, 375)::geometry
                    
                    -- Caso 2: 2 detecciones → buffer sobre la línea entre ambos
                    WHEN det_count = 2 THEN
                        ST_Buffer(
                            ST_MakeLine(
                                ST_GeometryN(points_geom, 1),
                                ST_GeometryN(points_geom, 2)
                            )::geography, 
                            200  -- 200m de ancho
                        )::geometry
                    
                    -- Caso 3: 3+ detecciones
                    ELSE
                        CASE
                            -- Si el ConvexHull es un polígono válido, usarlo
                            WHEN GeometryType(ST_ConvexHull(points_geom)) = 'POLYGON' THEN
                                ST_ConvexHull(points_geom)
                            
                            -- Si es un punto (todas las detecciones en el mismo lugar)
                            WHEN GeometryType(ST_ConvexHull(points_geom)) = 'POINT' THEN
                                ST_Buffer(ST_ConvexHull(points_geom)::geography, 375)::geometry
                            
                            -- Si es una línea (detecciones colineales) → buffer sobre la línea
                            WHEN GeometryType(ST_ConvexHull(points_geom)) IN ('LINESTRING', 'MULTILINESTRING') THEN
                                ST_Buffer(ST_ConvexHull(points_geom)::geography, 200)::geometry
                            
                            -- Fallback: buffer sobre el centroide
                            ELSE
                                ST_Buffer(centroid::geography, 375)::geometry
                        END
                END as calculated_geom
            FROM detection_stats
        )
        UPDATE fire_events fe
        SET
            -- Asegurar que sea POLYGON y tenga SRID 4326
            perimeter = CASE 
                WHEN GeometryType(ca.calculated_geom) IN ('POLYGON', 'MULTIPOLYGON') THEN
                    ST_SetSRID(ca.calculated_geom, 4326)::geography
                ELSE
                    ST_SetSRID(
                        ST_Buffer(ST_Centroid(ca.calculated_geom)::geography, 100)::geometry, 
                        4326
                    )::geography
            END,
            -- Área en hectáreas (Geography calcula en m², dividir por 10000)
            estimated_area_hectares = ROUND(
                (ST_Area(ca.calculated_geom::geography) / 10000)::numeric, 
                2
            ),
            updated_at = NOW()
        FROM calculated_areas ca
        WHERE fe.id = ca.event_id
        RETURNING fe.id;
    """)
    
    try:
        with engine.begin() as conn:
            result = conn.execute(sql)
            updated_count = result.rowcount
            
        logger.info(f"✅ Áreas calculadas para {updated_count} eventos")
        
        # Estadísticas finales
        with engine.connect() as conn:
            stats = conn.execute(text("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(estimated_area_hectares) as with_area,
                    ROUND(AVG(estimated_area_hectares)::numeric, 2) as avg_ha,
                    ROUND(MAX(estimated_area_hectares)::numeric, 2) as max_ha,
                    ROUND(MIN(estimated_area_hectares)::numeric, 2) as min_ha
                FROM fire_events
            """)).fetchone()
            
            logger.info(f"\n📊 Estadísticas de áreas:")
            logger.info(f"   Total eventos: {stats.total}")
            logger.info(f"   Con área calculada: {stats.with_area}")
            logger.info(f"   Área promedio: {stats.avg_ha} ha")
            logger.info(f"   Área máxima: {stats.max_ha} ha")
            logger.info(f"   Área mínima: {stats.min_ha} ha")
            
    except Exception as e:
        logger.error(f"❌ Error calculando áreas: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(
        description='Calcular perímetros y áreas de fire_events'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10000,
        help='Tamaño del batch (default: 10000)'
    )
    
    args = parser.parse_args()
    calculate_fire_areas(batch_size=args.batch_size)


if __name__ == "__main__":
    main()