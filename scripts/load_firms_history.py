"""
Descarga datos históricos de NASA FIRMS y los carga en la base de datos.
Soporta carga desde archivo local o descarga automática.

Uso:
    # Modo Descarga Automática
    python scripts/load_firms_history.py --year 2024 --satellite VIIRS
    
    # Modo Archivo Local 
    python scripts/load_firms_history.py --csv-path data/test_data.csv --limit 1000

Estrategia:
    - Normaliza datos de VIIRS/MODIS
    - Filtra espacialmente (solo Argentina)
    - Filtra por calidad (confidence >= 80%)
    - Inserta en lotes de 10,000 para performance
    - Dispara clustering automático al finalizar
"""

import argparse
import logging
import sys
import os
from pathlib import Path
from typing import Dict
from urllib.parse import urljoin
from sqlalchemy.engine import URL
import pandas as pd
import requests
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm
from dotenv import load_dotenv

# --- CONFIGURACIÓN DE ENTORNO ---
# Agregar directorio raíz al path para importar módulos (workers, app)
base_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(base_dir))
load_dotenv(dotenv_path=base_dir / ".env")

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuración Constante
NASA_FIRMS_BASE_URL = "https://firms.modaps.eosdis.nasa.gov/data/country/"
ARGENTINA_BBOX = {
    'min_lat': -55.0,  # Ushuaia
    'max_lat': -21.0,  # Jujuy
    'min_lon': -73.5,  # Mendoza oeste
    'max_lon': -53.0   # Misiones este
}

class FIRMSDownloader:
    """Descargador de datos históricos de NASA FIRMS"""
    
    def __init__(self, download_dir: Path = Path("data/raw/firms")):
        self.download_dir = download_dir
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
    def get_bulk_file_url(self, satellite: str, year: int) -> str:
        if satellite.upper() == 'VIIRS':
            filename = f"viirs-snpp_{year}_Argentina.csv"
        elif satellite.upper() == 'MODIS':
            filename = f"modis_{year}_Argentina.csv"
        else:
            raise ValueError(f"Satélite no soportado: {satellite}")
        
        return urljoin(NASA_FIRMS_BASE_URL, filename)
    
    def download_file(self, url: str, output_path: Path) -> Path:
        logger.info(f"Descargando desde: {url}")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        with open(output_path, 'wb') as f, tqdm(
            desc=output_path.name,
            total=total_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
        ) as pbar:
            for chunk in response.iter_content(chunk_size=8192):
                size = f.write(chunk)
                pbar.update(size)
        
        logger.info(f"Descargado: {output_path}")
        return output_path
    
    def download_year(self, satellite: str, year: int) -> Path:
        url = self.get_bulk_file_url(satellite, year)
        output_filename = f"{satellite.lower()}_{year}_argentina.csv"
        output_path = self.download_dir / output_filename
        
        if output_path.exists():
            logger.info(f"Archivo ya existe: {output_path}")
            return output_path
        
        return self.download_file(url, output_path)


class FIRMSProcessor:
    """Procesador de datos FIRMS"""
    
    @staticmethod
    def normalize_confidence(row: Dict) -> int:
        conf_raw = str(row.get('confidence', ''))
        if conf_raw.lower() in ['l', 'low']: return 33
        elif conf_raw.lower() in ['n', 'nominal']: return 66
        elif conf_raw.lower() in ['h', 'high']: return 100
        else:
            try:
                return int(float(conf_raw))
            except (ValueError, TypeError):
                return 0
    
    def filter_argentina(self, df: pd.DataFrame) -> pd.DataFrame:
        mask = (
            (df['latitude'] >= ARGENTINA_BBOX['min_lat']) &
            (df['latitude'] <= ARGENTINA_BBOX['max_lat']) &
            (df['longitude'] >= ARGENTINA_BBOX['min_lon']) &
            (df['longitude'] <= ARGENTINA_BBOX['max_lon'])
        )
        return df[mask]
    
    def filter_high_confidence(self, df: pd.DataFrame, threshold: int = 80) -> pd.DataFrame:
        # Copia para evitar SettingWithCopyWarning
        df = df.copy()
        df['confidence_normalized'] = df.apply(self.normalize_confidence, axis=1)
        return df[df['confidence_normalized'] >= threshold]
    
    def prepare_for_db(self, df: pd.DataFrame, satellite: str) -> pd.DataFrame:
        """
        Normaliza el dataframe FIRMS (MODIS/VIIRS) al esquema fire_detections v3.1
        CORRECCIÓN: Formatea acquisition_time a HH:MM:SS para evitar error de tipo en Postgres.
        """

        # Renombrar columnas directas
        column_mapping = {
            'frp': 'fire_radiative_power',
            'acq_date': 'acquisition_date',
            'acq_time': 'acquisition_time',
            'confidence': 'confidence_raw',
            'daynight': 'daynight',
            'latitude': 'latitude',
            'longitude': 'longitude',
        }

        df_renamed = df.rename(columns=column_mapping).copy()

        # --- Temperaturas normalizadas (combinar MODIS/VIIRS) ---
        mir_modis = df.get('brightness')    # MODIS
        mir_viirs = df.get('bright_ti4')    # VIIRS
        if mir_modis is not None and mir_viirs is not None:
            df_renamed['bt_mir_kelvin'] = mir_modis.combine_first(mir_viirs)
        elif mir_modis is not None:
            df_renamed['bt_mir_kelvin'] = mir_modis
        elif mir_viirs is not None:
            df_renamed['bt_mir_kelvin'] = mir_viirs
        else:
            df_renamed['bt_mir_kelvin'] = None

        tir_modis = df.get('bright_t31')    # MODIS
        tir_viirs = df.get('bright_ti5')    # VIIRS
        if tir_modis is not None and tir_viirs is not None:
            df_renamed['bt_tir_kelvin'] = tir_modis.combine_first(tir_viirs)
        elif tir_modis is not None:
            df_renamed['bt_tir_kelvin'] = tir_modis
        elif tir_viirs is not None:
            df_renamed['bt_tir_kelvin'] = tir_viirs
        else:
            df_renamed['bt_tir_kelvin'] = None

        # --- Instrumentación ---
        df_renamed['satellite'] = satellite.upper()
        df_renamed['instrument'] = 'VIIRS' if 'VIIRS' in satellite.upper() else 'MODIS'

        # --- Manejo de Fechas y Horas ---
        # 1. Asegurar que acq_time sea string de 4 dígitos (ej: 510 -> "0510")
        if 'acquisition_time' in df_renamed.columns:
            acq_time_str = (
                df_renamed['acquisition_time']
                .astype(str)
                .str.replace(r'\.0$', '', regex=True)
                .str.zfill(4)
            )
            
            # 2. ✅ CORRECCIÓN CRÍTICA: Convertir a formato SQL Time (HH:MM:SS)
            # Esto evita el error "integer vs time" en la base de datos
            df_renamed['acquisition_time'] = (
                acq_time_str.str.slice(0, 2) + ':' + 
                acq_time_str.str.slice(2, 4) + ':00'
            )
        else:
            acq_time_str = '0000'
            df_renamed['acquisition_time'] = None

        # 3. Crear timestamp completo con zona horaria
        df_renamed['detected_at'] = pd.to_datetime(
            df_renamed['acquisition_date'].astype(str) + ' ' + acq_time_str,
            format='%Y-%m-%d %H%M',
            errors='coerce',
            utc=True
        )

        # --- Geometría PostGIS ---
        df_renamed['location'] = df_renamed.apply(
            lambda row: f"POINT({row['longitude']} {row['latitude']})",
            axis=1
        )

        # --- Selección Final de Columnas ---
        # NO incluimos bt_delta_kelvin porque es generada automáticamente
        columns_to_keep = [
            'satellite',
            'instrument',
            'detected_at',
            'latitude',
            'longitude',
            'location',
            'bt_mir_kelvin',
            'bt_tir_kelvin',
            'fire_radiative_power',
            'confidence_raw',
            'confidence_normalized',
            'acquisition_date',
            'acquisition_time',
            'daynight',
        ]

        # Rellenar columnas faltantes con None
        for col in columns_to_keep:
            if col not in df_renamed.columns:
                df_renamed[col] = None

        return df_renamed[columns_to_keep]


class FIRMSLoader:
    """Cargador de datos FIRMS a PostgreSQL"""
    
    def __init__(self, database_url: str = None):
        
        # 1. ESTRATEGIA: CONSTRUCCIÓN DINÁMICA (La que recordabas)
        # Si tenemos las variables sueltas en el .env, construimos la URL segura
        if os.getenv("DB_PASSWORD") and os.getenv("DB_HOST"):
            logger.info("🔧 Construyendo URL de base de datos segura desde variables de entorno...")
            
            # SQLAlchemy se encarga de codificar los símbolos raros (@, :, /) automáticamente
            url_object = URL.create(
                "postgresql",
                username=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD"), # <--- ACÁ ESTÁ LA MAGIA
                host=os.getenv("DB_HOST"),
                port=int(os.getenv("DB_PORT", 5432)),
                database=os.getenv("DB_NAME", "postgres")
            )
            self.engine = create_engine(url_object)
            
        # 2. ESTRATEGIA: FALLBACK (URL completa)
        elif database_url:
            # Fix para SQLAlchemy uri (postgres:// -> postgresql://)
            if database_url.startswith("postgres://"):
                database_url = database_url.replace("postgres://", "postgresql://", 1)
            
            self.engine = create_engine(database_url)
            
        else:
            raise ValueError("❌ No se encontraron credenciales. Configura DB_PASSWORD/DB_HOST en .env o pasa --database-url")
    
    def load_batch(self, df: pd.DataFrame, batch_size: int = 10000):
        total_rows = len(df)
        if total_rows == 0:
            logger.warning("⚠️ No hay registros para cargar.")
            return

        logger.info(f"💾 Cargando {total_rows} registros en lotes de {batch_size}")
        
        # Usar inserción SQL directa para manejar geometría correctamente si pandas falla
        # Pero por ahora usaremos to_sql estándar para simplicidad, asumiendo que PostGIS
        # puede castear el string POINT(...) a geometry automáticamente si la columna es geometry
        
        # NOTA IMPORTANTE: Para que PostGIS lea 'POINT(x y)' como geometría desde pandas,
        # a veces es necesario usar GeoAlchemy o una query raw. 
        # Aquí usamos un truco: insertamos como texto, Postgres lo castea.
        
        with tqdm(total=total_rows, desc="Insertando en DB") as pbar:
            for start_idx in range(0, total_rows, batch_size):
                end_idx = min(start_idx + batch_size, total_rows)
                batch = df.iloc[start_idx:end_idx]
                
                # Insertar
                batch.to_sql(
                    'fire_detections',
                    self.engine,
                    if_exists='append',
                    index=False,
                    method='multi',
                    chunksize=1000
                )
                pbar.update(len(batch))
        
        logger.info(f"✅ Cargados {total_rows} registros exitosamente")


def main():
    parser = argparse.ArgumentParser(description='Carga datos históricos de NASA FIRMS (Local o Descarga)')
    
    # Argumentos para MODO LOCAL
    parser.add_argument('--csv-path', type=str, help='Ruta a archivo CSV local')
    parser.add_argument('--limit', type=int, help='Límite de registros a procesar (para testing)')
    
    # Argumentos para MODO DESCARGA
    parser.add_argument('--year', type=int, default=2024, help='Año a descargar')
    parser.add_argument('--satellite', type=str, choices=['VIIRS', 'MODIS'], default='VIIRS', help='Satélite')
    parser.add_argument('--skip-download', action='store_true', help='No descargar si ya existe')
    
    # Argumentos GENERALES
    parser.add_argument('--confidence-threshold', type=int, default=80, help='Umbral de confianza')
    parser.add_argument('--database-url', type=str, default=os.getenv('DATABASE_URL'), help='URL Base de datos')
    parser.add_argument('--skip-clustering', action='store_true', help='Saltar paso de clustering')
    
    args = parser.parse_args()

    # Aceptar dos formas de credenciales:
    # 1) DATABASE_URL
    # 2) DB_HOST + DB_PASSWORD (+ opcionales DB_USER/DB_PORT/DB_NAME)
    has_dynamic_env = bool(os.getenv("DB_HOST") and os.getenv("DB_PASSWORD"))

    if not (args.database_url or has_dynamic_env):
        logger.error("❌ No se encontraron credenciales. Configura DB_HOST/DB_PASSWORD en .env o pasa --database-url.")
        return


    # 1. OBTENCIÓN DEL ARCHIVO (Local vs Descarga)
    if args.csv_path:
        csv_path = Path(args.csv_path)
        if not csv_path.exists():
            logger.error(f"❌ Archivo no encontrado: {csv_path}")
            return
        logger.info(f"📂 Usando archivo local: {csv_path}")
    else:
        logger.info(f"🌐 Iniciando modo descarga para {args.satellite} {args.year}")
        downloader = FIRMSDownloader()
        csv_path = downloader.download_year(args.satellite, args.year)

    # 2. LECTURA Y FILTRADO
    logger.info("📖 Leyendo archivo CSV...")
    
    # Aplicar límite si existe
    if args.limit:
        logger.info(f"✂️ Aplicando límite de lectura: {args.limit} registros")
        df = pd.read_csv(csv_path, nrows=args.limit)
    else:
        df = pd.read_csv(csv_path)
    
    logger.info(f"Total registros leídos: {len(df):,}")
    
    processor = FIRMSProcessor()
    
    # Filtrar espacialmente
    df_argentina = processor.filter_argentina(df)
    logger.info(f"Registros en Argentina: {len(df_argentina):,}")
    
    # Filtrar por confianza
    df_filtered = processor.filter_high_confidence(df_argentina, args.confidence_threshold)
    logger.info(f"Registros Alta Confianza (>{args.confidence_threshold}): {len(df_filtered):,}")
    
    # Preparar columnas
    df_prepared = processor.prepare_for_db(df_filtered, args.satellite)
    
    # 3. CARGA EN BD
    loader = FIRMSLoader(args.database_url)
    loader.load_batch(df_prepared)
    
    # 4. CLUSTERING AUTOMÁTICO
    if not args.skip_clustering and not df_prepared.empty:
        logger.info("🔄 Disparando clustering automático...")
        try:
            # Importación dinámica para evitar errores circulares si workers no está listo
            from workers.tasks.clustering import run_clustering_task
            
            # Nota: Podríamos pasar el rango de fechas cargado para optimizar
            min_date = df_prepared['acquisition_date'].min()
            max_date = df_prepared['acquisition_date'].max()
            logger.info(f"📅 Ejecutando clustering para rango: {min_date} a {max_date}")
            
            # Ejecutar tarea (puedes ajustar según cómo esté definida tu tarea de Celery)
            # Si es celery task: run_clustering_task.delay(...)
            # Si es función local: run_clustering_task(...)
            # Aquí asumimos invocación directa para el script de carga
            try:
                run_clustering_task() 
                logger.info("✅ Clustering finalizado.")
            except Exception as e:
                logger.warning(f"⚠️ Clustering falló (pero los datos se cargaron): {e}")
                
        except ImportError:
            logger.warning("⚠️ No se encontró el módulo 'workers.tasks.clustering'. Saltando agrupación.")
    
    logger.info("✨ Proceso finalizado.")

if __name__ == '__main__':
    main()