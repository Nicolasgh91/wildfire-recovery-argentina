import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
from shapely.geometry import Point, MultiPoint
import logging

logger = logging.getLogger(__name__)

def cluster_fire_detections(df: pd.DataFrame):
    if df.empty:
        return pd.DataFrame()

    # --- 1. Filtro de Confianza ---
    conf_map = {'l': 30, 'n': 80, 'h': 100, 'low': 30, 'nominal': 80, 'high': 100}
    df['conf_num'] = df['confidence'].map(lambda x: conf_map.get(str(x).lower(), 50))
    df = df[df['conf_num'] >= 80].copy()
    
    if df.empty: return pd.DataFrame()

    # --- 2. Clustering Espacio-Temporal ---
    kms_per_radian = 6371.0088
    epsilon = 0.5 / kms_per_radian 
    coords = np.radians(df[['latitude', 'longitude']].values)
    db = DBSCAN(eps=epsilon, min_samples=1, metric='haversine').fit(coords)
    df['spatial_cluster'] = db.labels_

    df['acq_date'] = pd.to_datetime(df['acq_date'])
    df = df.sort_values(['spatial_cluster', 'acq_date'])
    df['time_diff'] = df.groupby('spatial_cluster')['acq_date'].diff().dt.days.fillna(0)
    df['new_event_flag'] = (df['time_diff'] > 3).astype(int)
    df['unique_event_id'] = df.groupby('spatial_cluster')['new_event_flag'].cumsum()
    df['final_cluster_id'] = df['spatial_cluster'].astype(str) + "_" + df['unique_event_id'].astype(str)

    # --- 3. Agregación y Generación de Polígonos ---
    unique_events = []
    
    for cid, group in df.groupby('final_cluster_id'):
        points = [Point(xy) for xy in zip(group['longitude'], group['latitude'])]
        multi_point = MultiPoint(points)
        centroid = multi_point.centroid
        
        # Generación de Polígono compatible con tu esquema (GEOMETRY(Polygon, 4326))
        # Forzamos a que siempre sea un Polygon, incluso con 1 solo punto
        if len(points) >= 3:
            boundary = multi_point.convex_hull
            # Si el convex_hull resulta ser un punto o línea (puntos alineados), aplicamos buffer
            if boundary.geom_type != 'Polygon':
                boundary = boundary.buffer(0.005) 
        else:
            # Para 1 o 2 puntos, creamos un área circular (buffer) que cuenta como Polygon
            boundary = centroid.buffer(0.005)

        event_data = {
            "fecha_deteccion": group['acq_date'].min().date(),
            "latitud": float(centroid.y),
            "longitud": float(centroid.x),
            "geometria": boundary.wkt, # PostGIS se encarga del SRID si el engine está bien
            "total_detections": int(len(group)),
            "sum_frp": float(group['frp'].sum()),
            "avg_confidence": float(group['conf_num'].mean()),
            # Metadata para el filtro
            "max_frp": float(group['max_frp'].max() if 'max_frp' in group else group['frp'].max())
        }
        
        # Filtro de Significancia (Filtro 3)
        if event_data['sum_frp'] > 100 or event_data['total_detections'] >= 5:
            unique_events.append(event_data)
            
    return pd.DataFrame(unique_events)