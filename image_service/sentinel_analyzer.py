import os
import sys
import argparse  # <--- Nuevo: Para recibir parámetros
import ee
import requests
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from io import BytesIO
from PIL import Image

# --- CONFIGURACIÓN ---
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")
OUTPUT_FOLDER = _PROJECT_ROOT / "output_images"
OUTPUT_FOLDER.mkdir(exist_ok=True)

# --- TU ID DE PROYECTO GEE (Actualizado) ---
GEE_PROJECT_ID = "forest-guard-484400"

class FireRecoveryAnalyzerGEE:
    def __init__(self):
        # 1. Inicializar Earth Engine
        try:
            ee.Initialize(project=GEE_PROJECT_ID)
            # print("✅ Conexión GEE exitosa.") # Comentado para limpiar output en CLI
        except Exception as e:
            print(f"⚠️ Error inicializando GEE: {e}")
            try:
                ee.Authenticate()
                ee.Initialize(project=GEE_PROJECT_ID)
            except Exception as e2:
                print(f"❌ Error crítico GEE: {e2}")
                sys.exit(1)

        self.db_engine = self._get_db_engine()

    def _get_db_engine(self):
        import urllib.parse
        uri = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
        if not uri: return None
        try:
            if "://" in uri and "@" in uri:
                prefix, rest = uri.split("://", 1)
                if "@" in rest:
                    auth, host = rest.rsplit("@", 1)
                    if ":" in auth:
                        u, p = auth.split(":", 1)
                        uri = f"{prefix}://{u}:{urllib.parse.quote_plus(p)}@{host}"
        except: pass
        if "sslmode=" not in uri: uri += "&sslmode=require" if "?" in uri else "?sslmode=require"
        return create_engine(uri)

    def get_fire_data(self, incendio_id):
        query = text("SELECT fecha_deteccion, latitud, longitud FROM incendios WHERE id = :id")
        with self.db_engine.connect() as conn:
            result = conn.execute(query, {"id": incendio_id}).fetchone()
        return result

    def fetch_gee_image(self, lat, lon, start_date, end_date, pixel_size):
        """
        Obtiene imágenes RGB, NDVI y SWIR.
        pixel_size: Define la resolución (512 para baja, 1280 para alta).
        """
        roi = ee.Geometry.Point([lon, lat]).buffer(5000) # 5km radio

        s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
            .filterDate(start_date, end_date) \
            .filterBounds(roi) \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30)) \
            .sort('CLOUDY_PIXEL_PERCENTAGE')

        if s2.size().getInfo() == 0:
            return None, None, None

        image = s2.first().clip(roi)

        # 1. RGB
        url_rgb = image.getThumbURL({
            'min': 0, 'max': 3000, 'bands': ['B4', 'B3', 'B2'],
            'dimensions': pixel_size, 'region': roi, 'format': 'png'
        })

        # 2. NDVI
        ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
        url_ndvi = ndvi.getThumbURL({
            'min': -0.1, 'max': 0.8,
            'palette': ['black', 'red', 'orange', 'yellow', 'green'], 
            'dimensions': pixel_size, 'region': roi, 'format': 'png'
        })

        # 3. SWIR (Falso Color)
        url_swir = image.getThumbURL({
            'min': 0, 'max': 4000, 'bands': ['B12', 'B8', 'B4'],
            'dimensions': pixel_size, 'region': roi, 'format': 'png'
        })

        return url_rgb, url_ndvi, url_swir

    def download_image_from_url(self, url):
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        return np.array(img)


    def get_land_cover(self, lat, lon, year):
        """
        Consulta el tipo de suelo usando MODIS Land Cover en GEE.
        Retorna la etiqueta (ej: 'Bosque', 'Pastizal').
        """
        try:
            # Usamos el dataset MODIS MCD12Q1 (Land Cover Type 1)
            # Tomamos el año anterior al incendio para saber qué había antes
            dataset = ee.ImageCollection("MODIS/006/MCD12Q1") \
                .filterDate(f'{year-1}-01-01', f'{year-1}-12-31') \
                .first()
            
            if not dataset:
                return "Datos no disponibles"

            point = ee.Geometry.Point([lon, lat])
            
            # Obtenemos el valor de la clasificación (Type 1)
            land_cover = dataset.select('LC_Type1').reduceRegion(
                reducer=ee.Reducer.first(),
                geometry=point,
                scale=500
            ).getInfo()

            lc_code = land_cover.get('LC_Type1')

            # Diccionario oficial de la IGBP (International Geosphere-Biosphere Programme)
            igbp_classes = {
                1: "Bosque de Coníferas Perenne",
                2: "Bosque de Coníferas Caducifolio",
                3: "Bosque de Hojas Anchas Perenne",
                4: "Bosque de Hojas Anchas Caducifolio",
                5: "Bosque Mixto",
                6: "Matorral Cerrado",
                7: "Matorral Abierto",
                8: "Sabana Leñosa",
                9: "Sabana",
                10: "Pastizal",
                11: "Humedal Permanente",
                12: "Tierras de Cultivo",
                13: "Urbano / Construido",
                14: "Mosaico Cultivo/Vegetación",
                15: "Nieve / Hielo",
                16: "Árido / Desierto",
                17: "Agua"
            }
            
            return igbp_classes.get(lc_code, "No Clasificado")

        except Exception as e:
            print(f"⚠️ Error obteniendo Land Cover: {e}")
            return "No determinado"

    def analyze_recovery(self, incendio_id, calidad="alta"):
        print(f"🔥 Analizando ID: {incendio_id} | Calidad: {calidad.upper()}")
        
        # Configuración según calidad
        if calidad == "alta":
            pixel_size = 1280
            dpi_val = 150
        else:
            pixel_size = 512
            dpi_val = 72

        data = self.get_fire_data(incendio_id)
        if not data:
            print(f"❌ Error: El incendio {incendio_id} no existe en la DB.")
            return
        
        lat, lon, fecha = float(data.latitud), float(data.longitud), data.fecha_deteccion
        print(f"📍 {lat}, {lon} ({fecha})")

        timeline = {
            "pre": (fecha - timedelta(days=60), fecha - timedelta(days=1)),
            "post_immediate": (fecha + timedelta(days=1), fecha + timedelta(days=45)),
            "post_1_year": (fecha + timedelta(days=335), fecha + timedelta(days=395)),
        }

        images_rgb = {}
        images_ndvi = {}
        images_swir = {}

        print("☁️ Consultando satélites (esto puede tardar unos segundos)...")
        for key, (start, end) in timeline.items():
            try:
                # Pasamos pixel_size dinámico
                url_rgb, url_ndvi, url_swir = self.fetch_gee_image(lat, lon, start.isoformat(), end.isoformat(), pixel_size)
                
                if url_rgb:
                    images_rgb[key] = self.download_image_from_url(url_rgb)
                    images_ndvi[key] = self.download_image_from_url(url_ndvi)
                    images_swir[key] = self.download_image_from_url(url_swir)
                    # print(f"   ✅ {key}: OK") # Verbose opcional
                else:
                    print(f"   ⚠️ {key}: No encontrada (nubes/falta datos)")
            except Exception as e:
                print(f"   ❌ Error en {key}: {e}")

        if not images_rgb:
            print("❌ No se pudieron descargar imágenes.")
            return

        # Visualización
        cols = len(images_rgb)
        fig, axs = plt.subplots(3, cols, figsize=(5 * cols, 15))
        
        idx = 0
        ordered_keys = ["pre", "post_immediate", "post_1_year"]
        
        for key in ordered_keys:
            if key in images_rgb:
                if cols > 1:
                    ax_rgb, ax_swir, ax_ndvi = axs[0, idx], axs[1, idx], axs[2, idx]
                else:
                    ax_rgb, ax_swir, ax_ndvi = axs[0], axs[1], axs[2]

                ax_rgb.imshow(images_rgb[key])
                ax_rgb.set_title(f"{key.upper()}\n(Color Real)", fontsize=10)
                ax_rgb.axis('off')

                ax_swir.imshow(images_swir[key])
                ax_swir.set_title(f"DETECCIÓN (SWIR)", fontsize=10, color='darkred', fontweight='bold')
                ax_swir.axis('off')

                ax_ndvi.imshow(images_ndvi[key])
                ax_ndvi.set_title(f"SALUD (NDVI)", fontsize=10)
                ax_ndvi.axis('off')
                
                idx += 1

        plt.suptitle(f"Reporte {calidad.upper()} - Incendio {incendio_id}", fontsize=16)
        plt.tight_layout()
        
        filename = f"analisis_{incendio_id}_{calidad}.png"
        output_path = OUTPUT_FOLDER / filename
        plt.savefig(output_path, dpi=dpi_val)
        print(f"✅ ¡LISTO! Imagen guardada: {output_path}")
        
        return output_path # <--- ESTO ES VITAL PARA LA API

if __name__ == "__main__":
    # Configuración de argumentos de línea de comandos
    parser = argparse.ArgumentParser(description="Generar reporte satelital de incendios.")
    
    # Argumento 1: ID del incendio (Obligatorio)
    parser.add_argument("id", type=str, help="UUID del incendio a analizar")
    
    # Argumento 2: Calidad (Opcional, default=alta)
    parser.add_argument("--calidad", choices=["alta", "baja"], default="alta", 
                        help="Calidad de imagen: 'alta' (HD, más lento) o 'baja' (rápido)")

    args = parser.parse_args()
    
    analyzer = FireRecoveryAnalyzerGEE()
    analyzer.analyze_recovery(args.id, calidad=args.calidad)