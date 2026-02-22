#!/usr/bin/env python3
"""
=============================================================================
FORESTGUARD - ENRIQUECIMIENTO ESPACIAL DE EVENTOS
=============================================================================

Asigna la provincia correspondiente a cada evento de incendio mediante
intersección espacial (Point in Polygon) con la tabla `regions`.

Uso:
    python scripts/enrich_location.py

Autor: ForestGuard Team
=============================================================================
"""
import sys
import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Configuración de entorno
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
load_dotenv(dotenv_path=BASE_DIR / ".env")

def get_db_url():
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME", "postgres")
    
    if not user or not host:
        return os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

def enrich_fire_locations():
    print("🌍 Iniciando enriquecimiento espacial...")
    
    engine = create_engine(get_db_url())
    
    # Esta es la misma query SQL optimizada, pero ejecutada desde Python
    sql_query = text("""
        UPDATE fire_events
        SET province = regions.name
        FROM regions
        WHERE ST_Intersects(regions.geom, fire_events.centroid) 
          AND regions.category = 'PROVINCIA'
          AND fire_events.province IS NULL;
    """)
    
    with engine.begin() as connection:
        result = connection.execute(sql_query)
        print(f"✅ Se actualizaron {result.rowcount} incendios con su provincia correspondiente.")

if __name__ == "__main__":
    enrich_fire_locations()