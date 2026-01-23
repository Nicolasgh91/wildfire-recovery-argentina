"""
Notebook para preprocesar datos de NASA FIRMS
Agrupa detecciones en incendios únicos usando clustering espacial-temporal
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.cluster import DBSCAN
from geopy.distance import geodesic

# ========== 1. CARGAR DATOS ==========

print("Cargando CSV de NASA FIRMS...")
df = pd.read_csv('../raw_data/nasa_detections_2015_2026.csv')

print(f"Total de detecciones: {len(df):,}")
print(f"Rango de fechas: {df['acq_date'].min()} a {df['acq_date'].max()}")
print(f"\nPrimeras filas:")
print(df.head())

# ========== 2. LIMPIEZA Y FILTRADO ==========

print("\n--- Filtrado de datos ---")

# Convertir fecha
df['fecha'] = pd.to_datetime(df['acq_date'])

# Filtro 1: Solo confianza nominal o alta
# confidence: n=nominal, h=high, l=low
df_filtrado = df[df['confidence'].isin(['n', 'h'])].copy()
print(f"Después de filtrar confianza: {len(df_filtrado):,} ({len(df_filtrado)/len(df)*100:.1f}%)")

# Filtro 2: Solo detecciones nocturnas (menos falsos positivos)
# daynight: D=day, N=night
df_filtrado = df_filtrado[df_filtrado['daynight'] == 'N']
print(f"Después de filtrar nocturnos: {len(df_filtrado):,}")

# Filtro 3: FRP mínimo (intensidad del fuego)
# FRP > 1 MW sugiere incendio real, no anomalía térmica
df_filtrado = df_filtrado[df_filtrado['frp'] > 1.0]
print(f"Después de filtrar FRP>1: {len(df_filtrado):,}")

# ========== 3. CLUSTERING ESPACIAL-TEMPORAL ==========

print("\n--- Clustering de detecciones ---")

# Preparar datos para clustering
# Normalizar coordenadas espaciales y temporales

# Convertir fecha a timestamp numérico (días desde época)
df_filtrado['dias_desde_epoca'] = (
    df_filtrado['fecha'] - df_filtrado['fecha'].min()
).dt.days

# Crear matriz de features: [lat, lon, dias]
# Escalamos días para que 1 día ≈ 0.005 grados (~500m)
X = df_filtrado[['latitude', 'longitude', 'dias_desde_epoca']].values
X[:, 2] = X[:, 2] * 0.005  # Escalar tiempo

# DBSCAN clustering
# eps=0.005 ≈ 500m en coordenadas geográficas
# min_samples=3 → mínimo 3 detecciones para considerar incendio
print("Ejecutando DBSCAN...")
clustering = DBSCAN(eps=0.005, min_samples=3, metric='euclidean')
df_filtrado['cluster'] = clustering.fit_predict(X)

# Resultados
n_clusters = len(set(df_filtrado['cluster'])) - (1 if -1 in df_filtrado['cluster'] else 0)
n_noise = list(df_filtrado['cluster']).count(-1)

print(f"\nIncendios únicos identificados: {n_clusters:,}")
print(f"Detecciones aisladas (ruido): {n_noise:,}")

# ========== 4. CREAR DATASET DE INCENDIOS ==========

print("\n--- Generando dataset de incendios ---")

# Agrupar por cluster
incendios = []

for cluster_id in df_filtrado['cluster'].unique():
    if cluster_id == -1:  # Ignorar ruido
        continue
    
    cluster_data = df_filtrado[df_filtrado['cluster'] == cluster_id]
    
    # Estadísticas del cluster
    incendio = {
        'cluster_id': cluster_id,
        'latitud': cluster_data['latitude'].mean(),
        'longitud': cluster_data['longitude'].mean(),
        'fecha_primera_deteccion': cluster_data['fecha'].min().date(),
        'fecha_ultima_deteccion': cluster_data['fecha'].max().date(),
        'duracion_dias': (cluster_data['fecha'].max() - cluster_data['fecha'].min()).days,
        'num_detecciones': len(cluster_data),
        'frp_max': cluster_data['frp'].max(),
        'frp_promedio': cluster_data['frp'].mean(),
        'brightness_max': cluster_data['brightness'].max(),
        # Área aproximada (distancia entre puntos extremos)
        'lat_min': cluster_data['latitude'].min(),
        'lat_max': cluster_data['latitude'].max(),
        'lon_min': cluster_data['longitude'].min(),
        'lon_max': cluster_data['longitude'].max(),
    }
    
    # Calcular área aproximada en hectáreas
    # Distancia norte-sur
    dist_ns = geodesic(
        (incendio['lat_min'], incendio['longitud']),
        (incendio['lat_max'], incendio['longitud'])
    ).meters
    
    # Distancia este-oeste
    dist_eo = geodesic(
        (incendio['latitud'], incendio['lon_min']),
        (incendio['latitud'], incendio['lon_max'])
    ).meters
    
    # Área aproximada (asumiendo rectángulo)
    area_m2 = dist_ns * dist_eo
    incendio['area_hectareas'] = round(area_m2 / 10000, 2)
    
    incendios.append(incendio)

df_incendios = pd.DataFrame(incendios)

print(f"Dataset final: {len(df_incendios):,} incendios únicos")
print(f"\nEstadísticas:")
print(f"  Duración promedio: {df_incendios['duracion_dias'].mean():.1f} días")
print(f"  Área promedio: {df_incendios['area_hectareas'].mean():.1f} hectáreas")
print(f"  FRP promedio: {df_incendios['frp_promedio'].mean():.2f} MW")

# ========== 5. ANÁLISIS DE INCENDIOS QUE CRUZAN AÑOS ==========

print("\n--- Incendios que cruzan años ---")

df_incendios['año_inicio'] = pd.to_datetime(df_incendios['fecha_primera_deteccion']).dt.year
df_incendios['año_fin'] = pd.to_datetime(df_incendios['fecha_ultima_deteccion']).dt.year

incendios_multi_año = df_incendios[df_incendios['año_inicio'] != df_incendios['año_fin']]
print(f"Incendios que cruzan años: {len(incendios_multi_año)}")

if len(incendios_multi_año) > 0:
    print("\nEjemplos:")
    print(incendios_multi_año[['cluster_id', 'fecha_primera_deteccion', 'fecha_ultima_deteccion', 'duracion_dias']].head(10))

# ========== 6. FILTRAR TOP INCENDIOS PARA ANÁLISIS ==========

print("\n--- Selección de incendios para análisis ---")

# Criterios de selección:
# 1. Área significativa (>50 hectáreas)
# 2. Duración mínima (>2 días)
# 3. FRP significativo (>5 MW promedio)

df_para_analisis = df_incendios[
    (df_incendios['area_hectareas'] > 50) &
    (df_incendios['duracion_dias'] > 2) &
    (df_incendios['frp_promedio'] > 5)
].copy()

print(f"Incendios que cumplen criterios: {len(df_para_analisis)}")

# Ordenar por relevancia (combinación de área, duración, intensidad)
df_para_analisis['score'] = (
    df_para_analisis['area_hectareas'] * 0.4 +
    df_para_analisis['duracion_dias'] * 10 * 0.3 +
    df_para_analisis['frp_promedio'] * 20 * 0.3
)

df_para_analisis = df_para_analisis.sort_values('score', ascending=False)

print(f"\nTop 10 incendios más significativos:")
print(df_para_analisis[['fecha_primera_deteccion', 'area_hectareas', 'duracion_dias', 'frp_promedio', 'score']].head(10))

# ========== 7. GUARDAR RESULTADOS ==========

print("\n--- Guardando resultados ---")

# Guardar dataset completo
df_incendios.to_csv('incendios_procesados_completo.csv', index=False)
print("✓ Guardado: incendios_procesados_completo.csv")

# Guardar top incendios para análisis (primeros 100)
df_para_analisis.head(100).to_csv('incendios_para_analisis.csv', index=False)
print("✓ Guardado: incendios_para_analisis.csv (top 100)")

# Distribución por año
print("\n--- Distribución por año ---")
distribucion_anual = df_incendios.groupby('año_inicio').size()
print(distribucion_anual)

print("\n✓ Preprocesamiento completado")