import os
import sys
import time
import urllib.parse  # <--- IMPORTANTE: Para arreglar la contraseña
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# --- CONFIGURACIÓN ---
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

# Reutilizamos tu lógica de conexión segura
def get_safe_db_uri():
    # Buscar DATABASE_URL o SUPABASE_DB_URL
    uri = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not uri:
        print("❌ Error: No se encontró DATABASE_URL ni SUPABASE_DB_URL en .env")
        return None
    
    # --- FIX CRÍTICO: CODIFICAR CONTRASEÑA ---
    try:
        # Si la URI tiene el formato estándar postgresql://user:pass@host:port/db
        if "://" in uri and "@" in uri:
            prefix, rest = uri.split("://", 1)
            # Usamos rsplit para separar por el ÚLTIMO arroba (el que separa auth de host)
            if "@" in rest:
                auth_part, host_part = rest.rsplit("@", 1)
                
                # Separamos usuario y contraseña
                if ":" in auth_part:
                    user, password = auth_part.split(":", 1)
                    
                    # Codificamos la contraseña (cambia @ por %40, etc.)
                    safe_password = urllib.parse.quote_plus(password)
                    
                    # Reconstruimos la URI
                    uri = f"{prefix}://{user}:{safe_password}@{host_part}"
    except Exception as e:
        print(f"⚠️ Advertencia: No se pudo codificar la contraseña automáticamente: {e}")
        # Si falla, intentamos usar la URI original

    # Asegurar SSL
    if "sslmode=" not in uri:
        separator = "&" if "?" in uri else "?"
        uri += f"{separator}sslmode=require"
    
    return uri

# Validación de URI antes de crear el motor
DB_URI = get_safe_db_uri()
if not DB_URI:
    raise ValueError("No se pudo obtener la URI de la base de datos.")

# Creamos el motor
engine = create_engine(DB_URI)

def run_overlaps_history():
    print("--- 🕵️‍♂️ Iniciando Cálculo Histórico de Superposiciones ---")
    
    # Iteramos desde 2015 hasta 2026
    for year in range(2015, 2027):
        print(f"\n📅 Procesando Año: {year}...", end="", flush=True)
        start_t = time.time()
        
        # La query optimizada (inyectamos el año dinámicamente)
        query = text(f"""
        INSERT INTO superposiciones (incendio_a_id, incendio_b_id, porcentaje_superposicion, area_superpuesta_hectareas, dias_transcurridos)
        SELECT 
            LEAST(a.id, b.id),
            GREATEST(a.id, b.id),
            (ST_Area(ST_Intersection(a.geometria::geography, b.geometria::geography)) / LEAST(ST_Area(a.geometria::geography), ST_Area(b.geometria::geography))) * 100,
            ST_Area(ST_Intersection(a.geometria::geography, b.geometria::geography)) / 10000,
            ABS(a.fecha_deteccion - b.fecha_deteccion)
        FROM incendios a
        JOIN incendios b ON a.id < b.id 
        WHERE 
            -- Filtramos A por el año actual
            a.fecha_deteccion >= '{year}-01-01' AND a.fecha_deteccion <= '{year}-12-31'
            -- Filtros espaciales
            AND a.geometria && b.geometria 
            AND ST_Intersects(a.geometria, b.geometria)
            AND (ST_Area(ST_Intersection(a.geometria::geography, b.geometria::geography)) / LEAST(ST_Area(a.geometria::geography), ST_Area(b.geometria::geography))) * 100 >= 5
        ON CONFLICT (incendio_a_id, incendio_b_id) DO NOTHING;
        """)
        
        try:
            with engine.begin() as conn:  # begin() maneja commit automáticamente
                conn.execute(query)
            elapsed = time.time() - start_t
            print(f" ✅ Listo ({elapsed:.2f}s)")
        except Exception as e:
            print(f" ❌ Error: {e}")

    print("\n🏁 ¡Cálculo histórico finalizado!")

if __name__ == "__main__":
    run_overlaps_history()