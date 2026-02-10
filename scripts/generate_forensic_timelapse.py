import os
import ee
import geemap
from dotenv import load_dotenv
from google.oauth2 import service_account

# 1. Cargar variables de entorno
load_dotenv()

PROJECT_ID = os.getenv("GEE_PROJECT_ID")
SERVICE_ACCOUNT = os.getenv("GEE_SERVICE_ACCOUNT_EMAIL")
KEY_PATH = os.getenv("GEE_PRIVATE_KEY_PATH")

def initialize_gee():
    """Autenticación robusta usando Service Account"""
    try:
        if not PROJECT_ID:
            raise ValueError("❌ Faltan variables de entorno GEE_PROJECT_ID")

        print(f"🔐 Iniciando sesión en GEE como: {SERVICE_ACCOUNT}...")
        
        # Verificar si existe el archivo de clave
        if KEY_PATH and os.path.exists(KEY_PATH):
            # 👇 Definimos el permiso específico que necesita Earth Engine
            SCOPES = ['https://www.googleapis.com/auth/earthengine']

            # 👇 Creamos las credenciales con ese alcance
            credentials = service_account.Credentials.from_service_account_file(
                KEY_PATH, 
                scopes=SCOPES
            )
            ee.Initialize(credentials=credentials, project=PROJECT_ID)
            print("✅ Autenticación exitosa con Service Account.")
        else:
            # Fallback a autenticación interactiva si no hay JSON (solo para desarrollo local)
            print(f"⚠️ No se encontró el archivo de clave en: {KEY_PATH}")
            print("   Intentando autenticación interactiva (navegador)...")
            ee.Authenticate()
            ee.Initialize(project=PROJECT_ID)
            
    except Exception as e:
        print(f"❌ Error crítico inicializando GEE: {str(e)}")
        exit(1)

def generate_forensic_gif(lat, lon, fire_date_str, output_filename="forensic_evidence.gif"):
    print(f"🛰️  Analizando coordenadas: {lat}, {lon} para el evento de {fire_date_str}...")

    # Configuración del punto y ROI (Radio de 2km para contexto)
    point = ee.Geometry.Point([lon, lat])
    roi = point.buffer(2000).bounds()

    # Fechas Clave
    fire_year = int(fire_date_str.split('-')[0])
    # Visualizamos: 1 año antes, el año del incendio, y los 3 posteriores
    years_to_visualize = [fire_year - 1, fire_year, fire_year + 1, fire_year + 2, fire_year + 3]

    # Colección Sentinel-2
    s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
        .filterBounds(roi) \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 15))

    images = []
    
    # Textos para estampar en el GIF (opcional, requiere paquete extra, lo omitimos por simplicidad visual)
    
    for year in years_to_visualize:
        # Buscamos ventana de verano (Oct-Marzo) donde la vegetación es más activa
        # Si es un incendio en invierno, la cicatriz se ve mejor en primavera.
        start = f"{year}-10-01"
        end = f"{year + 1}-03-30"
        
        # Reductor mediano para eliminar nubes
        img = s2.filterDate(start, end).median().clip(roi)
        
        # Visualización Falso Color (SWIR/NIR/Red) - Estándar para incendios
        # Bandas Sentinel-2: B12 (SWIR2), B8 (NIR), B4 (Red