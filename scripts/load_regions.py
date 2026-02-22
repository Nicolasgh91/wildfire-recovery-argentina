#!/usr/bin/env python3
"""
=============================================================================
FORESTGUARD - CARGA DE LIMITES PROVINCIALES (IGN)
=============================================================================

Descarga y procesa los límites provinciales oficiales de Argentina desde
el servicio WFS del Instituto Geográfico Nacional (IGN).

Funcionalidad:
1. Consulta WFS del IGN para obtener capa 'ign:provincia'
2. Procesa GeoJSON y simplifica/valida geometrías
3. Inserta o actualiza la tabla `regions` (category='PROVINCIA')

Uso:
    python scripts/load_regions.py

Requisitos:
    - Conexión a internet (wms.ign.gob.ar)
    - Base de datos configurada en .env

Autor: ForestGuard Team
=============================================================================
"""
import sys
import os
import requests
import json
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from geoalchemy2.shape import from_shape
from shapely.geometry import shape, MultiPolygon, Polygon
from dotenv import load_dotenv

# --- CONFIGURACIÓN DE ENTORNO ---
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
load_dotenv(dotenv_path=BASE_DIR / ".env")

# Importaciones
try:
    from app.models.region import Region
    from app.db.base import Base
except ImportError as e:
    print(f"❌ Error de importación: {e}")
    sys.exit(1)

# --- FUENTE OFICIAL: INSTITUTO GEOGRÁFICO NACIONAL (IGN) ---
# Usamos el servicio WFS (Web Feature Service) para pedir el GeoJSON
IGN_WFS_URL = "https://wms.ign.gob.ar/geoserver/ign/ows"

def get_db_url():
    """Construye la URL de conexión."""
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME", "postgres")
    
    if not user or not host:
        url = os.getenv("DATABASE_URL", "")
        return url.replace("postgres://", "postgresql://")
        
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

def load_provinces():
    print(f"⬇️ Consultando Servidor Oficial del IGN (wms.ign.gob.ar)...")
    
    params = {
        "service": "wfs",
        "version": "1.1.0",
        "request": "GetFeature",
        "typeName": "ign:provincia",  # Capa oficial de provincias
        "outputFormat": "application/json"
    }

    try:
        # verify=False a veces es necesario en servidores del estado por temas de certificados
        # pero intentamos primero con True por seguridad.
        response = requests.get(IGN_WFS_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"❌ Error descargando datos del IGN: {e}")
        return

    # Conectar a la DB
    try:
        engine = create_engine(get_db_url())
        Session = sessionmaker(bind=engine)
        session = Session()
        # Limpiar índices residuales que puedan provocar errores de creación
        try:
            with engine.begin() as conn:
                conn.execute(text('DROP INDEX IF EXISTS "idx_protected_areas_boundary" CASCADE'))
                conn.execute(text('DROP INDEX IF EXISTS "idx_regions_geom" CASCADE'))
        except Exception:
            pass
        Base.metadata.create_all(engine)
    except Exception as e:
        print(f"❌ Error conectando a DB: {e}")
        return

    features = data.get('features', [])
    print(f"🌍 IGN devolvió {len(features)} jurisdicciones. Procesando...")
    
    count_new = 0
    count_skip = 0
    
    for feature in features:
        props = feature['properties']
        geom_json = feature['geometry']
        
        # El IGN usa distintos códigos según la capa ('nam', 'fna', 'nombre')
        # Buscamos cualquiera que tenga datos
        name = props.get('nam') or props.get('fna') or props.get('nombre')
        
        if not name:
            print(f"   ⚠️ Saltando registro sin nombre: {props}")
            continue

        try:
            # 1. Convertir JSON a Geometría (Shapely)
            shapely_geom = shape(geom_json)
            
            # 2. Asegurar que sea MultiPolygon
            if isinstance(shapely_geom, Polygon):
                shapely_geom = MultiPolygon([shapely_geom])
                
            # 3. Convertir a WKB
            wkb_element = from_shape(shapely_geom, srid=4326)
            
            # 4. Verificar existencia
            exists = session.query(Region).filter_by(name=name, category="PROVINCIA").first()
            
            if not exists:
                region = Region(
                    name=name,
                    category="PROVINCIA",
                    geom=wkb_element
                )
                session.add(region)
                count_new += 1
                print(f"   ✅ Cargada: {name}")
            else:
                count_skip += 1
                
        except Exception as e:
            print(f"   ❌ Error procesando {name}: {e}")

    session.commit()
    session.close()
    print(f"\n✨ Resumen: {count_new} nuevas insertadas, {count_skip} ya existían.")

if __name__ == "__main__":
    load_provinces()