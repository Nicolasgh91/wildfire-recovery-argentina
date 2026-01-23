import os
import sys
import urllib.parse  # Needed to fix password issues
import pandas as pd
import numpy as np
import logging
import time
import geopandas as gpd
from shapely import wkt
from pathlib import Path
from dotenv import load_dotenv
from multiprocessing import Pool, cpu_count
from fire_processor import cluster_fire_detections
from sqlalchemy import create_engine, text



# --- PATH SETUP ---
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SERVICES_DIR = Path(__file__).resolve().parent

load_dotenv(_PROJECT_ROOT / ".env")

# Ensure imports work even if run from different folders
if str(_SERVICES_DIR) not in sys.path:
    sys.path.insert(0, str(_SERVICES_DIR))


# --- LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ParallelProcessor")

# --- DATABASE URI FIX ---
def get_safe_db_uri():
    uri = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not uri:
        return None
    
    # 1. Check for SSL. Supabase often requires it.
    if "sslmode=" not in uri:
        separator = "&" if "?" in uri else "?"
        uri += f"{separator}sslmode=require"
    
    # 2. Fix Password Encoding
    # If your password has special chars, SQLAlchemy fails.
    # We split the URI to encode ONLY the password part.
    try:
        if "@" in uri and ":" in uri:
            prefix, rest = uri.split("://", 1)
            user_pass, host_db = rest.rsplit("@", 1)
            user, password = user_pass.split(":", 1)
            # Encode password
            safe_password = urllib.parse.quote_plus(password)
            return f"{prefix}://{user}:{safe_password}@{host_db}"
    except Exception:
        logger.warning("Could not manually encode password, using URI as is.")
    
    return uri

DB_URI = get_safe_db_uri()
CSV_PATH = _PROJECT_ROOT / "raw_data" / "nasa_detections_2015_2026.csv"

# Updated SQL: Using GEOMETRY for PostGIS compatibility
CREATE_TABLE_IF_NOT_EXISTS = """
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE TABLE IF NOT EXISTS unique_fire_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    centroid GEOMETRY(Point, 4326),
    area_boundary GEOMETRY(Polygon, 4326),
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    duration_days INTEGER,
    total_detections INTEGER,
    avg_frp DOUBLE PRECISION,
    max_frp DOUBLE PRECISION,
    sum_frp DOUBLE PRECISION,
    avg_confidence DOUBLE PRECISION,
    is_significant BOOLEAN,
    year_group INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
"""

def worker_process(payload):
    year, batch_df = payload
    start_time = time.time()
    processed_events = cluster_fire_detections(batch_df)
    
    if not processed_events.empty:
        processed_events['year_group'] = year
        elapsed = time.time() - start_time
        return processed_events, f"✅ Year {year} finished in {elapsed:.2f}s ({len(processed_events)} events)"
    
    return pd.DataFrame(), f"⚠️ Year {year} had no significant events."

def run_parallel_ingest():
    print(f"--- 🚀 Starting Parallel Batch Ingestion ---")
    
    # Pre-checks
    if not CSV_PATH.exists():
        print(f"❌ CSV not found at {CSV_PATH}")
        return
    if not DB_URI:
        print("❌ DATABASE_URL missing in .env")
        return

    # Test Connection immediately before processing
    engine = create_engine(DB_URI)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("🔗 Database connection verified.")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

    # 1. Load and Filter
    df = pd.read_csv(CSV_PATH)
    df["acq_date"] = pd.to_datetime(df["acq_date"])
    hoy = pd.Timestamp.now().normalize()
    df = df[df["acq_date"].dt.normalize() <= hoy].copy()
    
    years = sorted(df["acq_date"].dt.year.unique())

    # 2. Payloads
    payloads = []
    for i, year in enumerate(years):
        if i > 0:
            prev_year_end = df[(df['acq_date'].dt.year == years[i-1]) & (df['acq_date'].dt.day >= 29)]
            curr_year = df[df['acq_date'].dt.year == year]
            batch_df = pd.concat([prev_year_end, curr_year])
        else:
            batch_df = df[df['acq_date'].dt.year == year]
        payloads.append((year, batch_df))

    # 3. Parallel Execution
    with Pool(processes=max(1, cpu_count() - 1)) as pool:
        results = pool.map(worker_process, payloads)

    # 4. Consolidate
    all_dfs = [res[0] for res in results if not res[0].empty]
    for _, log in results: print(log)

    if all_dfs:
        final_df = pd.concat(all_dfs)
        
        # Eliminamos duplicados basados en los nombres que vienen del fire_processor
        final_df = final_df.drop_duplicates(subset=['latitud', 'longitud', 'fecha_deteccion'])
        
        print(f"\n--- 🏁 Total Unique Events: {len(final_df)} ---")

        try:
            # Preparar para tabla 'incendios'
            # Convertimos el WKT string a objetos geométricos para calcular área
            from shapely import wkt
            final_df['geometry_obj'] = final_df['geometria'].apply(wkt.loads)
            gdf = gpd.GeoDataFrame(final_df, geometry='geometry_obj', crs="EPSG:4326")
            
            # Calculamos hectáreas proyectando a metros (EPSG:3857)
            final_df['area_afectada_hectareas'] = gdf.to_crs(epsg=3857).area / 10000

            # Preparar datos para inserción
            final_df['estado_analisis'] = 'pendiente'
            final_df['tipo'] = 'nuevo'
            final_df['provincia'] = None  # Se puede determinar después si es necesario

            print(f"Enviando {len(final_df)} incendios a la tabla 'incendios'...")
            
            # Subida a la DB usando SQL directo para manejar PostGIS correctamente
            engine = create_engine(DB_URI)
            
            # Preparar datos para inserción
            records = []
            for _, row in final_df.iterrows():
                # Asegurar que fecha_deteccion sea un objeto date
                fecha = row['fecha_deteccion']
                if isinstance(fecha, pd.Timestamp):
                    fecha = fecha.date()
                elif isinstance(fecha, str):
                    fecha = pd.to_datetime(fecha).date()
                
                records.append({
                    'fecha_deteccion': fecha,
                    'latitud': float(row['latitud']),
                    'longitud': float(row['longitud']),
                    'area_afectada_hectareas': float(row['area_afectada_hectareas']) if pd.notna(row['area_afectada_hectareas']) else None,
                    'geometria': str(row['geometria']),  # WKT string
                    'estado_analisis': str(row['estado_analisis']),
                    'tipo': str(row['tipo']),
                    'provincia': row.get('provincia')
                })
            
            # Insertar usando SQL directo con ST_GeomFromText para PostGIS
            insert_sql = text("""
                INSERT INTO incendios (
                    fecha_deteccion, latitud, longitud, 
                    area_afectada_hectareas, geometria,
                    estado_analisis, tipo, provincia
                ) VALUES (
                    :fecha_deteccion, :latitud, :longitud,
                    :area_afectada_hectareas, 
                    ST_GeomFromText(:geometria, 4326),
                    :estado_analisis, :tipo, :provincia
                )
            """)
            
            # Insertar en lotes usando executemany para mejor rendimiento
            chunk_size = 500  # Reducido para evitar problemas de memoria
            total_inserted = 0
            with engine.begin() as conn:
                for i in range(0, len(records), chunk_size):
                    chunk = records[i:i + chunk_size]
                    try:
                        # Intentar con executemany (SQLAlchemy 2.0+)
                        conn.execute(insert_sql, chunk)
                    except (TypeError, AttributeError):
                        # Fallback: insertar uno por uno si executemany no funciona
                        for record in chunk:
                            conn.execute(insert_sql, record)
                    total_inserted += len(chunk)
                    if (i // chunk_size) % 10 == 0 or i + chunk_size >= len(records):
                        print(f"  Insertados {total_inserted} de {len(records)} registros...")
            
            print("🎉 Base de datos 'incendios' actualizada correctamente.")

        except Exception as e:
            import traceback
            print(f"❌ Error durante el procesamiento final o subida: {e}")
            print(f"❌ Traceback completo:")
            traceback.print_exc()
    else:
        print("❌ No se procesaron datos significativos.")

if __name__ == "__main__":
    total_start = time.time()
    run_parallel_ingest()
    print(f"\n⌛ Total Execution Time: {time.time() - total_start:.2f} seconds")