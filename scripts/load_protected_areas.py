#!/usr/bin/env python3
"""
=============================================================================
FORESTGUARD - SCRIPT DE CARGA DE ÁREAS PROTEGIDAS
=============================================================================

Descarga y carga los polígonos de áreas protegidas de Argentina en la base 
de datos PostGIS para el cálculo de prohibiciones legales (Ley 26.815).

Fuentes de datos soportadas:
---------------------------
1. IGN (Instituto Geográfico Nacional) - RECOMENDADO
   - URL: https://www.ign.gob.ar/NuestrasActividades/InformacionGeoespacial/CapasSIG
   - Formato: GeoJSON/Shapefile
   - Cobertura: Nacional + Provincial (~100 áreas)
   
2. Protected Planet (WDPA)
   - URL: https://www.protectedplanet.net/country/ARG
   - Formato: Shapefile (requiere descarga manual)
   - Cobertura: Completa (473 áreas)
   
3. Archivo local (GeoJSON/Shapefile)
   - Para datasets custom o ya descargados

Uso:
----
    # Opción 1: Descargar desde IGN (por defecto)
    python scripts/load_protected_areas.py
    
    # Opción 2: Desde archivo local
    python scripts/load_protected_areas.py --source local --file /path/to/areas.geojson
    
    # Opción 3: Desde URL directa
    python scripts/load_protected_areas.py --source url --url https://example.com/areas.geojson
    
    # Opciones adicionales
    python scripts/load_protected_areas.py --dry-run           # Solo validar, no insertar
    python scripts/load_protected_areas.py --truncate          # Limpiar tabla antes de insertar
    python scripts/load_protected_areas.py --simplify 100      # Simplificar geometrías (metros)

Requisitos:
-----------
    pip install geopandas shapely sqlalchemy geoalchemy2 requests

Autor: ForestGuard Team
Fecha: 2025-01
=============================================================================
"""

import argparse
import logging
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import geopandas as gpd
import requests
from shapely import wkt
from shapely.geometry import MultiPolygon, Polygon, mapping
from shapely.validation import make_valid
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

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

# URLs de fuentes de datos conocidas
DATA_SOURCES = {
    "ign": {
        "name": "Instituto Geográfico Nacional",
        "url": "https://wms.ign.gob.ar/geoserver/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=ign:area_protegida&outputFormat=application/json",
        "format": "geojson",
        "field_mapping": {
            "nam": "official_name",
            "gna": "category",
            "jur": "jurisdiction",
        }
    },
    "apn_wfs": {
        "name": "Administración de Parques Nacionales (WFS)",
        "url": "http://mapas.parquesnacionales.gob.ar/geoserver/wfs?service=WFS&version=1.0.0&request=GetFeature&typeName=geonode:apn_areasprotegidas&outputFormat=application/json",
        "format": "geojson",
        "field_mapping": {
            "nombre": "official_name",
            "categoria": "category",
            "provincia": "province",
        }
    },
}

# Mapeo de categorías del IGN a nuestro sistema
CATEGORY_MAPPING = {
    # IGN / APN nomenclature
    "parque nacional": "national_park",
    "reserva nacional": "national_reserve",
    "monumento natural": "natural_monument",
    "reserva natural estricta": "national_reserve",
    "reserva natural silvestre": "national_reserve",
    "parque provincial": "provincial_park",
    "reserva provincial": "provincial_reserve",
    "reserva natural provincial": "provincial_reserve",
    "area natural protegida": "provincial_reserve",
    "reserva de biosfera": "biosphere_reserve",
    "sitio ramsar": "ramsar_site",
    "patrimonio mundial": "world_heritage",
    "reserva municipal": "municipal_reserve",
    "reserva privada": "private_reserve",
    "refugio de vida silvestre": "wildlife_refuge",
    "area marina protegida": "marine_park",
    "parque marino": "marine_park",
    # Fallback
    "otra": "other",
    "otros": "other",
}

# Mapeo de jurisdicciones
JURISDICTION_MAPPING = {
    "nacional": "national",
    "national": "national",
    "federal": "national",
    "provincial": "provincial",
    "municipal": "municipal",
    "privada": "private",
    "private": "private",
}


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def get_database_url() -> str:
    """
    Obtiene la URL de la base de datos desde variables de entorno.
    
    Returns:
        str: URL de conexión a PostgreSQL
    """
    import os
    
    # Intentar cargar desde .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    # Construir URL desde componentes individuales (para Supabase)
    db_host = os.getenv("SUPABASE_DB_HOST") or os.getenv("DB_HOST")
    db_port = os.getenv("SUPABASE_DB_PORT") or os.getenv("DB_PORT", "5432")
    db_name = os.getenv("SUPABASE_DB_NAME") or os.getenv("DB_NAME")
    db_user = os.getenv("SUPABASE_DB_USER") or os.getenv("DB_USER")
    db_password = os.getenv("SUPABASE_DB_PASSWORD") or os.getenv("DB_PASSWORD")
    
    if all([db_host, db_name, db_user, db_password]):
        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    # Fallback: URL completa
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url
    
    raise ValueError(
        "No se encontró configuración de base de datos. "
        "Definí DATABASE_URL o las variables SUPABASE_DB_* en tu .env"
    )


def normalize_category(raw_category: str) -> str:
    """
    Normaliza la categoría del área protegida a nuestro sistema interno.
    
    Args:
        raw_category: Categoría original del dataset
        
    Returns:
        str: Categoría normalizada
        
    Example:
        >>> normalize_category("Parque Nacional")
        'national_park'
        >>> normalize_category("RESERVA PROVINCIAL")
        'provincial_reserve'
    """
    if not raw_category:
        return "other"
    
    normalized = raw_category.lower().strip()
    return CATEGORY_MAPPING.get(normalized, "other")


def normalize_jurisdiction(raw_jurisdiction: str) -> Optional[str]:
    """
    Normaliza la jurisdicción a nuestro sistema interno.
    
    Args:
        raw_jurisdiction: Jurisdicción original
        
    Returns:
        str | None: Jurisdicción normalizada
    """
    if not raw_jurisdiction:
        return None
    
    normalized = raw_jurisdiction.lower().strip()
    return JURISDICTION_MAPPING.get(normalized)


def ensure_multipolygon(geom) -> MultiPolygon:
    """
    Convierte cualquier geometría a MultiPolygon válido.
    
    Args:
        geom: Geometría de Shapely (Polygon o MultiPolygon)
        
    Returns:
        MultiPolygon: Geometría convertida y validada
    """
    # Validar geometría
    if not geom.is_valid:
        geom = make_valid(geom)
    
    # Convertir a MultiPolygon si es Polygon
    if isinstance(geom, Polygon):
        return MultiPolygon([geom])
    elif isinstance(geom, MultiPolygon):
        return geom
    else:
        # Intentar extraer polígonos de geometrías complejas
        logger.warning(f"Geometría inesperada: {geom.geom_type}, intentando extraer polígonos")
        polygons = [g for g in geom.geoms if isinstance(g, (Polygon, MultiPolygon))]
        if polygons:
            return MultiPolygon(polygons)
        raise ValueError(f"No se pudo convertir {geom.geom_type} a MultiPolygon")


def calculate_area_hectares(geom) -> float:
    """
    Calcula el área en hectáreas usando proyección UTM.
    
    Args:
        geom: Geometría en WGS84
        
    Returns:
        float: Área en hectáreas
    """
    import pyproj
    from shapely.ops import transform
    
    # Determinar zona UTM basada en el centroide
    centroid = geom.centroid
    utm_zone = int((centroid.x + 180) / 6) + 1
    hemisphere = "south" if centroid.y < 0 else "north"
    
    # Crear transformación a UTM
    utm_crs = f"+proj=utm +zone={utm_zone} +{hemisphere} +ellps=WGS84 +datum=WGS84 +units=m +no_defs"
    project = pyproj.Transformer.from_crs(
        "EPSG:4326", 
        utm_crs, 
        always_xy=True
    ).transform
    
    # Transformar y calcular área
    geom_utm = transform(project, geom)
    area_m2 = geom_utm.area
    
    return area_m2 / 10000  # Convertir a hectáreas


def download_data(source: str, url: Optional[str] = None) -> gpd.GeoDataFrame:
    """
    Descarga datos de áreas protegidas desde la fuente especificada.
    
    Args:
        source: Nombre de la fuente ('ign', 'apn_wfs', 'url')
        url: URL personalizada (si source='url')
        
    Returns:
        GeoDataFrame: Datos descargados
    """
    if source == "url" and url:
        target_url = url
        logger.info(f"📥 Descargando desde URL personalizada: {url}")
    elif source in DATA_SOURCES:
        target_url = DATA_SOURCES[source]["url"]
        logger.info(f"📥 Descargando desde {DATA_SOURCES[source]['name']}")
        logger.info(f"   URL: {target_url}")
    else:
        raise ValueError(f"Fuente desconocida: {source}")
    
    try:
        # Detectar formato por extensión o content-type
        response = requests.get(target_url, timeout=60)
        response.raise_for_status()
        
        # Guardar en archivo temporal
        with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False) as f:
            f.write(response.content)
            temp_path = f.name
        
        # Cargar con GeoPandas
        gdf = gpd.read_file(temp_path)
        logger.info(f"✅ Descargados {len(gdf)} registros")
        
        # Limpiar archivo temporal
        Path(temp_path).unlink()
        
        return gdf
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Error de descarga: {e}")
        raise


def load_local_file(file_path: str) -> gpd.GeoDataFrame:
    """
    Carga datos desde un archivo local.
    
    Args:
        file_path: Ruta al archivo (GeoJSON, Shapefile, GeoPackage)
        
    Returns:
        GeoDataFrame: Datos cargados
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
    
    logger.info(f"📂 Cargando archivo local: {file_path}")
    
    # Si es un ZIP, extraer primero
    if path.suffix.lower() == ".zip":
        with tempfile.TemporaryDirectory() as tmpdir:
            with zipfile.ZipFile(path, 'r') as zip_ref:
                zip_ref.extractall(tmpdir)
            
            # Buscar shapefile dentro del ZIP
            shp_files = list(Path(tmpdir).rglob("*.shp"))
            if shp_files:
                gdf = gpd.read_file(shp_files[0])
            else:
                # Buscar GeoJSON
                json_files = list(Path(tmpdir).rglob("*.geojson")) + list(Path(tmpdir).rglob("*.json"))
                if json_files:
                    gdf = gpd.read_file(json_files[0])
                else:
                    raise ValueError("No se encontró shapefile ni GeoJSON en el ZIP")
    else:
        gdf = gpd.read_file(path)
    
    logger.info(f"✅ Cargados {len(gdf)} registros")
    return gdf


def process_geodataframe(
    gdf: gpd.GeoDataFrame,
    source: str,
    simplify_tolerance: Optional[float] = None
) -> List[Dict]:
    """
    Procesa el GeoDataFrame y lo convierte a lista de diccionarios para inserción.
    
    Args:
        gdf: GeoDataFrame con los datos
        source: Fuente de datos para el mapeo de campos
        simplify_tolerance: Tolerancia de simplificación en metros (opcional)
        
    Returns:
        List[Dict]: Lista de diccionarios listos para insertar
    """
    logger.info("🔄 Procesando datos...")
    
    # Asegurar CRS WGS84
    if gdf.crs is None:
        logger.warning("⚠️ CRS no definido, asumiendo WGS84")
        gdf = gdf.set_crs("EPSG:4326")
    elif gdf.crs != "EPSG:4326":
        logger.info(f"   Reproyectando de {gdf.crs} a WGS84")
        gdf = gdf.to_crs("EPSG:4326")
    
    # Obtener mapeo de campos para esta fuente
    field_mapping = {}
    if source in DATA_SOURCES:
        field_mapping = DATA_SOURCES[source].get("field_mapping", {})
    
    records = []
    errors = 0
    
    for idx, row in gdf.iterrows():
        try:
            # Extraer geometría
            geom = row.geometry
            if geom is None or geom.is_empty:
                logger.warning(f"   Fila {idx}: Geometría vacía, saltando")
                errors += 1
                continue
            
            # Convertir a MultiPolygon
            multi_geom = ensure_multipolygon(geom)
            
            # Simplificar si se especificó tolerancia
            if simplify_tolerance:
                multi_geom = multi_geom.simplify(simplify_tolerance / 111000)  # Convertir metros a grados aprox
            
            # Extraer campos usando el mapeo
            def get_field(target_field: str) -> Optional[str]:
                """Busca el valor del campo en la fila."""
                # Buscar en mapeo
                for source_field, mapped_field in field_mapping.items():
                    if mapped_field == target_field and source_field in row.index:
                        return row[source_field]
                
                # Buscar directamente por nombre común
                common_names = {
                    "official_name": ["nombre", "name", "nam", "NOMBRE", "NAME", "objeto"],
                    "category": ["categoria", "category", "gna", "CATEGORIA", "tipo", "type"],
                    "jurisdiction": ["jurisdiccion", "jurisdiction", "jur", "JURISDICCION"],
                    "province": ["provincia", "province", "prov", "PROVINCIA"],
                    "area_hectares": ["superficie", "area", "hectareas", "sup_ha", "SUPERFICIE"],
                }
                
                for common_name in common_names.get(target_field, []):
                    if common_name in row.index and row[common_name]:
                        return row[common_name]
                
                return None
            
            # Construir registro
            official_name = get_field("official_name") or f"Área Protegida {idx}"
            raw_category = get_field("category") or ""
            raw_jurisdiction = get_field("jurisdiction") or ""
            province = get_field("province")
            raw_area = get_field("area_hectares")
            
            # Calcular área si no está disponible
            if raw_area:
                try:
                    area_hectares = float(raw_area)
                except (ValueError, TypeError):
                    area_hectares = calculate_area_hectares(multi_geom)
            else:
                area_hectares = calculate_area_hectares(multi_geom)
            
            # Determinar años de prohibición según categoría
            category = normalize_category(raw_category)
            prohibition_years = 60 if category in [
                "national_park", "national_reserve", "natural_monument",
                "biosphere_reserve", "world_heritage"
            ] else 30
            
            record = {
                "official_name": str(official_name).strip(),
                "category": category,
                "jurisdiction": normalize_jurisdiction(raw_jurisdiction),
                "province": str(province).strip() if province else None,
                "prohibition_years": prohibition_years,
                "area_hectares": round(area_hectares, 2),
                "boundary_wkt": multi_geom.wkt,
                "centroid_wkt": multi_geom.centroid.wkt,
                "source_dataset": source.upper(),
            }
            
            records.append(record)
            
        except Exception as e:
            logger.warning(f"   Fila {idx}: Error procesando - {e}")
            errors += 1
            continue
    
    logger.info(f"✅ Procesados {len(records)} registros ({errors} errores)")
    return records


def insert_to_database(
    records: List[Dict],
    db_url: str,
    truncate: bool = False,
    dry_run: bool = False
) -> Tuple[int, int]:
    """
    Inserta los registros en la base de datos.
    
    Args:
        records: Lista de diccionarios a insertar
        db_url: URL de conexión a PostgreSQL
        truncate: Si True, limpia la tabla antes de insertar
        dry_run: Si True, solo valida sin insertar
        
    Returns:
        Tuple[int, int]: (insertados, errores)
    """
    if dry_run:
        logger.info("🔍 Modo DRY-RUN: validando sin insertar")
        return len(records), 0
    
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        if truncate:
            logger.info("🗑️ Limpiando tabla protected_areas...")
            session.execute(text("TRUNCATE TABLE protected_areas CASCADE"))
            session.commit()
        
        logger.info(f"💾 Insertando {len(records)} registros...")
        
        inserted = 0
        errors = 0
        
        for record in records:
            try:
                # Usar INSERT directo con ST_GeomFromText
                query = text("""
                    INSERT INTO protected_areas (
                        id,
                        official_name,
                        category,
                        jurisdiction,
                        province,
                        prohibition_years,
                        area_hectares,
                        boundary,
                        centroid,
                        source_dataset,
                        created_at,
                        updated_at
                    ) VALUES (
                        gen_random_uuid(),
                        :official_name,
                        :category,
                        :jurisdiction,
                        :province,
                        :prohibition_years,
                        :area_hectares,
                        ST_GeomFromText(:boundary_wkt, 4326)::geography,
                        ST_GeomFromText(:centroid_wkt, 4326)::geography,
                        :source_dataset,
                        NOW(),
                        NOW()
                    )
                    ON CONFLICT DO NOTHING
                """)
                
                session.execute(query, record)
                inserted += 1
                
                # Commit cada 100 registros
                if inserted % 100 == 0:
                    session.commit()
                    logger.info(f"   Progreso: {inserted}/{len(records)}")
                    
            except Exception as e:
                logger.warning(f"   Error insertando '{record.get('official_name')}': {e}")
                errors += 1
                session.rollback()
                continue
        
        # Commit final
        session.commit()
        logger.info(f"✅ Insertados {inserted} registros ({errors} errores)")
        
        return inserted, errors
        
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Error en base de datos: {e}")
        raise
    finally:
        session.close()


# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def main():
    """Función principal del script."""
    parser = argparse.ArgumentParser(
        description="Carga áreas protegidas de Argentina en la base de datos PostGIS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  %(prog)s                                    # Usar fuente por defecto (IGN)
  %(prog)s --source apn_wfs                   # Usar WFS de Parques Nacionales
  %(prog)s --source local --file areas.geojson
  %(prog)s --source url --url https://example.com/areas.json
  %(prog)s --truncate                         # Limpiar tabla antes de insertar
  %(prog)s --dry-run                          # Solo validar, no insertar
  %(prog)s --simplify 100                     # Simplificar geometrías (100m)
        """
    )
    
    parser.add_argument(
        "--source",
        choices=["ign", "apn_wfs", "local", "url"],
        default="ign",
        help="Fuente de datos (default: ign)"
    )
    
    parser.add_argument(
        "--file",
        type=str,
        help="Ruta al archivo local (requerido si source=local)"
    )
    
    parser.add_argument(
        "--url",
        type=str,
        help="URL del GeoJSON (requerido si source=url)"
    )
    
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Limpiar tabla antes de insertar"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo validar, no insertar en BD"
    )
    
    parser.add_argument(
        "--simplify",
        type=float,
        metavar="METERS",
        help="Simplificar geometrías con tolerancia en metros"
    )
    
    args = parser.parse_args()
    
    # Validar argumentos
    if args.source == "local" and not args.file:
        parser.error("--file es requerido cuando source=local")
    
    if args.source == "url" and not args.url:
        parser.error("--url es requerido cuando source=url")
    
    # Banner
    logger.info("=" * 60)
    logger.info("🌲 FORESTGUARD - Carga de Áreas Protegidas")
    logger.info("=" * 60)
    logger.info(f"   Fuente: {args.source}")
    logger.info(f"   Truncate: {args.truncate}")
    logger.info(f"   Dry-run: {args.dry_run}")
    logger.info(f"   Simplify: {args.simplify}m" if args.simplify else "   Simplify: No")
    logger.info("=" * 60)
    
    try:
        # 1. Obtener URL de base de datos
        if not args.dry_run:
            db_url = get_database_url()
            logger.info(f"📊 Base de datos configurada")
        else:
            db_url = None
        
        # 2. Cargar datos
        if args.source == "local":
            gdf = load_local_file(args.file)
        else:
            gdf = download_data(args.source, args.url)
        
        # 3. Procesar datos
        records = process_geodataframe(
            gdf,
            source=args.source,
            simplify_tolerance=args.simplify
        )
        
        if not records:
            logger.error("❌ No se generaron registros para insertar")
            sys.exit(1)
        
        # 4. Mostrar resumen de categorías
        categories = {}
        for r in records:
            cat = r["category"]
            categories[cat] = categories.get(cat, 0) + 1
        
        logger.info("\n📊 Resumen por categoría:")
        for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
            logger.info(f"   {cat}: {count}")
        
        # 5. Insertar en base de datos
        if db_url:
            inserted, errors = insert_to_database(
                records,
                db_url,
                truncate=args.truncate,
                dry_run=args.dry_run
            )
        else:
            inserted, errors = len(records), 0
        
        # 6. Resumen final
        logger.info("\n" + "=" * 60)
        logger.info("✅ CARGA COMPLETADA")
        logger.info(f"   Total procesados: {len(records)}")
        logger.info(f"   Insertados: {inserted}")
        logger.info(f"   Errores: {errors}")
        logger.info("=" * 60)
        
        sys.exit(0 if errors == 0 else 1)
        
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
