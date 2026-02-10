#!/usr/bin/env python3
"""
=============================================================================
FORESTGUARD - DIAGNÓSTICO GEE FORENSIC
=============================================================================

Script de diagnóstico para verificar la autenticación y conectividad con
Google Earth Engine (GEE).

Funcionalidad:
1. Verifica variables de entorno (Credenciales)
2. Inicializa GEE
3. Intenta descargar un footprint pequeño para validar permisos

Uso:
    python scripts/debug_forensic.py

Autor: ForestGuard Team
=============================================================================
"""
import os
import sys
from dotenv import load_dotenv

# Forzar que los prints salgan inmediatemente a la consola
def log(msg):
    print(f"[DEBUG] {msg}", flush=True)

log("Iniciando script de diagnóstico...")

try:
    import ee
    import geemap
    from google.oauth2 import service_account
    log("Librerías importadas correctamente.")
except ImportError as e:
    log(f"ERROR CRÍTICO: Faltan librerías. {e}")
    sys.exit(1)

# 1. Cargar y Validar Variables de Entorno
log("Cargando archivo .env...")
load_dotenv()

PROJECT_ID = os.getenv("GEE_PROJECT_ID")
SERVICE_ACCOUNT = os.getenv("GEE_SERVICE_ACCOUNT_EMAIL")
KEY_PATH = os.getenv("GEE_PRIVATE_KEY_PATH")

log(f"   > PROJECT_ID: {PROJECT_ID}")
log(f"   > SERVICE_ACCOUNT: {SERVICE_ACCOUNT}")
log(f"   > KEY_PATH: {KEY_PATH}")

if not PROJECT_ID:
    log("❌ ERROR: No se encontró GEE_PROJECT_ID en el archivo .env")
    sys.exit(1)

# 2. Intentar Autenticación
def initialize_gee():
    log("Intentando autenticación con Google Earth Engine...")
    try:
        if KEY_PATH and os.path.exists(KEY_PATH):
            log(f"   > Usando llave JSON encontrada en: {os.path.abspath(KEY_PATH)}")
            # 👇 Definimos el permiso específico que necesita Earth Engine
            SCOPES = ['https://www.googleapis.com/auth/earthengine']

            # 👇 Creamos las credenciales con ese alcance
            credentials = service_account.Credentials.from_service_account_file(
                KEY_PATH, 
                scopes=SCOPES
            )
            ee.Initialize(credentials=credentials, project=PROJECT_ID)
            log("✅ ee.Initialize() exitoso con Service Account.")
        else:
            log("⚠️ No se encontró el JSON de Service Account. Usando autenticación interactiva.")
            ee.Authenticate()
            ee.Initialize(project=PROJECT_ID)
            log("✅ ee.Initialize() exitoso (Interactivo).")
            
        # Prueba de vida
        log("   > Probando conexión con servidor de Google...")
        test_msg = ee.String('Conexión OK').getInfo()
        log(f"   > Respuesta de Google: {test_msg}")
        
    except Exception as e:
        log(f"❌ ERROR DE CONEXIÓN GEE: {e}")
        sys.exit(1)

# 3. Generar Timelapse (Simplificado para test)
def run_test(lat, lon):
    log(f"Iniciando búsqueda de imágenes en {lat}, {lon}...")
    
    point = ee.Geometry.Point([lon, lat])
    roi = point.buffer(2000).bounds()
    
    # Buscamos SOLO UNA imagen para ver si hay datos
    collection = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
        .filterBounds(roi) \
        .filterDate('2020-01-01', '2020-12-31') \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 50)) # Relajamos filtro nubes

    size = collection.size().getInfo()
    log(f"📊 Imágenes encontradas en 2020 (con <50% nubes): {size}")

    if size > 0:
        log("Intentando descargar GIF de prueba...")
        try:
            # Configuración mínima para testear descarga
            vis_params = {'min': 0, 'max': 3000, 'bands': ['B4', 'B3', 'B2']} # RGB Real
            
            # Tomamos las primeras 3 imágenes para que sea rápido
            subset = collection.limit(3).map(lambda img: img.visualize(**vis_params))
            
            out_file = "test_debug.gif"
            geemap.download_ee_video(subset, {'region': roi, 'dimensions': 400, 'framesPerSecond': 1}, out_file)
            
            if os.path.exists(out_file):
                log(f"🎉 ¡ÉXITO! Se generó el archivo: {os.path.abspath(out_file)}")
            else:
                log("❌ El proceso terminó pero no veo el archivo GIF.")
        except Exception as e:
            log(f"❌ Error durante la descarga del video: {e}")
    else:
        log("⚠️ No se encontraron imágenes en esta zona. Revisa las coordenadas.")

if __name__ == "__main__":
    initialize_gee()
    # Coordenadas de tu candidato (Pre-Delta)
    run_test(-32.17042, -60.637355)