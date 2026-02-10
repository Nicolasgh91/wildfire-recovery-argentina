#!/usr/bin/env python3
"""
=============================================================================
FORESTGUARD - CONSOLIDACIÓN DE EVENTOS
=============================================================================

Fusiona eventos de incendio redundantes que representan el mismo fuego físico.

Criterios de fusión:
1. Proximidad Espacial: < 1000m (configurable)
2. Proximidad Temporal: Solapamiento o cercanía < 5 días
3. Coherencia Administrativa: Misma provincia

Uso:
    python scripts/consolidate_events.py

Autor: ForestGuard Team
=============================================================================
"""
import os
import sys
import logging
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_url():
    """Construye la URL de conexión a la base de datos desde variables de entorno."""
    url = os.getenv("DATABASE_URL")
    if not url and os.getenv("DB_HOST"):
        return f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    return url.replace("postgres://", "postgresql://", 1) if url else None

def consolidate_fire_events(distance_threshold_meters=1000, days_buffer=5):
    """
    Identifica y fusiona eventos de incendio redundantes basándose en proximidad
    espacial, temporal y administrativa (provincia).

    Reglas de Negocio para Unificación:
    -----------------------------------
    Un evento 'A' y un evento 'B' se consideran el mismo incendio si cumplen TODAS
    las siguientes condiciones simultáneamente:
    
    1. PROXIMIDAD ESPACIAL: Sus centroides están a una distancia menor o igual a 
       `distance_threshold_meters` (default: 1000m).
    
    2. CONTINUIDAD TEMPORAL: Existe un solapamiento o continuidad en sus fechas.
       Específicamente, el rango de fechas de uno debe tocar o estar dentro de los
       `days_buffer` días (default: 5 días) del otro.
       Fórmula: (Fin_A >= Inicio_B - 5 días) O (Fin_B >= Inicio_A - 5 días).
       
    3. COHERENCIA ADMINISTRATIVA: Ambos eventos deben pertenecer a la misma 
       provincia (campo `province`). Si uno tiene provincia NULL, se permite la fusión.

    4. ESTADO ACTIVO: Ambos eventos deben estar marcados como 'active'.
       No se fusionan eventos históricos ya cerrados para preservar la auditoría.

    Estrategia de Fusión (Merge Strategy):
    --------------------------------------
    - Se elige el evento con fecha de inicio más antigua como el "Sobreviviente" (Survivor).
    - El evento más nuevo se considera la "Víctima" (Victim).
    - Todas las detecciones (puntos satelitales) de la Víctima se reasignan al Sobreviviente.
    - Se recalculan las estadísticas del Sobreviviente (nuevo centroide, nuevas fechas min/max,
      total de detecciones, FRP máximo).
    - Se eliminan o reasignan las relaciones dependientes (intersecciones con áreas protegidas).
    - Se elimina físicamente el registro del evento Víctima.

    Args:
        distance_threshold_meters (int): Distancia máxima en metros para considerar fusión.
        days_buffer (int): Días de tolerancia temporal para considerar continuidad.
    """
    engine = create_engine(get_db_url())
    
    logger.info(f"🧩 Iniciando Consolidación de Eventos...")
    logger.info(f"   Reglas: Dist < {distance_threshold_meters}m | Buffer Temporal: +/- {days_buffer} días | Misma Provincia")
    
    with engine.begin() as conn:
        # 1. Encontrar pares de eventos candidatos
        # Usamos un Self-Join espacial y temporal
        query = text("""
            SELECT 
                a.id AS survivor_id,
                b.id AS victim_id,
                ST_Distance(a.centroid, b.centroid) as dist,
                a.province as prov_a,
                b.province as prov_b
            FROM fire_events a
            JOIN fire_events b 
              ON ST_DWithin(a.centroid, b.centroid, :dist) -- Regla Espacial
            WHERE 
              a.id < b.id  -- Evitar duplicados (A-B vs B-A) y auto-comparación
              AND a.status = 'active' 
              AND b.status = 'active'
              
              -- Regla Temporal: Rango de 5 días de tolerancia
              AND (a.end_date >= b.start_date - (:days || ' days')::INTERVAL 
                   OR b.end_date >= a.start_date - (:days || ' days')::INTERVAL)
                   
              -- Regla Administrativa: Misma provincia (o nulos)
              AND (a.province = b.province OR a.province IS NULL OR b.province IS NULL)
              
            ORDER BY a.start_date ASC -- El más viejo será el survivor por defecto en el orden
        """)
        
        pairs = conn.execute(query, {
            "dist": distance_threshold_meters,
            "days": days_buffer
        }).fetchall()
        
        if not pairs:
            logger.info("✅ No se encontraron eventos redundantes que cumplan las reglas.")
            return

        logger.info(f"🔥 Se encontraron {len(pairs)} pares de eventos para fusionar.")

        merged_count = 0
        processed_victims = set() # Para evitar intentar borrar el mismo evento dos veces en una pasada

        for p in pairs:
            survivor_id = p.survivor_id
            victim_id = p.victim_id
            
            # Verificar si este victim ya fue procesado en una iteración anterior de este loop
            if victim_id in processed_victims:
                continue
            
            # Verificar existencia en DB (por seguridad en concurrencia y cadenas de fusión)
            # Check Victim
            check_victim = conn.execute(text("SELECT id FROM fire_events WHERE id = :id"), {"id": victim_id}).fetchone()
            if not check_victim:
                continue

            # Check Survivor (puede haber sido borrado si era víctima en otro par anterior)
            check_survivor = conn.execute(text("SELECT id FROM fire_events WHERE id = :id"), {"id": survivor_id}).fetchone()
            if not check_survivor:
                logger.warning(f"⚠️ Survivor {survivor_id} no encontrado (posiblemente borrado en fusión previa). Saltando par.")
                continue

            # --- EJECUCIÓN DE LA FUSIÓN ---
            
            # A. Reasignar Detecciones (Hijos)
            conn.execute(text("""
                UPDATE fire_detections 
                SET fire_event_id = :survivor 
                WHERE fire_event_id = :victim
            """), {"survivor": survivor_id, "victim": victim_id})
            
            # B. Gestionar Intersecciones con Áreas Protegidas (Evitar Unique Constraint)
            # 1. Borrar intersecciones en la víctima que ya existen en el sobreviviente (duplicadas)
            conn.execute(text("""
                DELETE FROM fire_protected_area_intersections
                WHERE fire_event_id = :victim
                AND protected_area_id IN (
                    SELECT protected_area_id FROM fire_protected_area_intersections WHERE fire_event_id = :survivor
                )
            """), {"survivor": survivor_id, "victim": victim_id})
            
            # 2. Mover las intersecciones restantes (únicas) al sobreviviente
            conn.execute(text("""
                UPDATE fire_protected_area_intersections 
                SET fire_event_id = :survivor 
                WHERE fire_event_id = :victim
            """), {"survivor": survivor_id, "victim": victim_id})

            # 3. Reasignar otras dependencias (Foreign Keys)
            
            # A. CASO ESPECIAL: Forensic Cases (tiene Unique Constraint en fire_event_id + protected_area_id)
            # Primero borramos los casos de la víctima que colisionarían con los del sobreviviente
            conn.execute(text("""
                DELETE FROM forensic_cases
                WHERE fire_event_id = :victim
                AND protected_area_id IN (
                    SELECT protected_area_id FROM forensic_cases WHERE fire_event_id = :survivor
                )
            """), {"survivor": survivor_id, "victim": victim_id})
            
            # Luego movemos los restantes (que no tienen conflicto)
            conn.execute(text("""
                UPDATE forensic_cases
                SET fire_event_id = :survivor
                WHERE fire_event_id = :victim
            """), {"survivor": survivor_id, "victim": victim_id})

            # B. Tablas Genéricas (sin restricciones unique conflictivas conocidas)
            dependent_tables = [
                "land_use_changes", 
                "satellite_images", 
                "vegetation_monitoring", 
                "burn_certificates"
            ]
            
            for table in dependent_tables:
                conn.execute(text(f"""
                    UPDATE {table}
                    SET fire_event_id = :survivor
                    WHERE fire_event_id = :victim
                """), {"survivor": survivor_id, "victim": victim_id})
            
            # C. Recalcular Estadísticas del Sobreviviente
            # El evento consolidado tendrá la geometría envolvente de todos sus puntos
            conn.execute(text("""
                WITH aggregated AS (
                    SELECT 
                        COUNT(*) as total,
                        MIN(acquisition_date) as new_start,
                        MAX(acquisition_date) as new_end,
                        ST_Centroid(ST_Collect(location::geometry)) as new_center,
                        MAX(fire_radiative_power) as new_max_frp,
                        AVG(confidence_normalized) as new_avg_conf
                    FROM fire_detections
                    WHERE fire_event_id = :survivor
                )
                UPDATE fire_events
                SET 
                    total_detections = aggregated.total,
                    start_date = aggregated.new_start,
                    end_date = aggregated.new_end,
                    centroid = aggregated.new_center::geography,
                    max_frp = aggregated.new_max_frp,
                    avg_confidence = aggregated.new_avg_conf,
                    -- Eliminamos la actualización de province para evitar el error
                    updated_at = NOW()
                FROM aggregated
                WHERE id = :survivor
            """), {"survivor": survivor_id})
            
            # D. Eliminar Evento Víctima
            conn.execute(text("DELETE FROM fire_events WHERE id = :victim"), {"victim": victim_id})
            
            merged_count += 1
            processed_victims.add(victim_id)
            # logger.info(f"   MERGE EXITOSO: {victim_id} absorbido por {survivor_id}")

        logger.info(f"✅ Fusión completada. Se eliminaron {merged_count} eventos redundantes.")

if __name__ == "__main__":
    consolidate_fire_events()