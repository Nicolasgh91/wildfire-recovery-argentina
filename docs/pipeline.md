🌲 ForestGuard: Pipeline de Procesamiento de Incendios
Este documento detalla el flujo completo de datos ("El Trencito"), desde la descarga de datos satelitales crudos hasta la generación de alertas legales automáticas.

📋 Resumen del Flujo
1. Ingesta: NASA FIRMS (Puntos) -> DB (fire_detections)
2. Clustering: Puntos -> Eventos Únicos (fire_events)
3. Enriquecimiento: Eventos + Provincias (regions)
4. Geometría: Cálculo de Hectáreas Reales
5. Auditoría: Cruce con Parques Nacionales (protected_areas)

🚀 Ejecución Paso a Paso

Paso 1: Ingesta de Datos (Raw Data)
Descarga los puntos de calor (Hotspots) desde los servidores de la NASA (VIIRS/MODIS) y los guarda en bruto.
Script: scripts/load_firms_history.py  
Comando: scripts/load_firms_history.py --csv-path "data\raw\firms\nasa_detections_2015_2026.csv" 

Paso 2: Clustering (Agrupación)
Convierte puntos dispersos en "Eventos de Incendio" lógicos usando el algoritmo DBSCAN (densidad espacial y temporal).
Script: scripts/cluster_fire_events.py
Comando: python scripts/cluster_fire_events.py --start-date 2015-01-01 --end-date 2025-12-31
Resultado: Tabla fire_events poblada (pero sin provincia ni área calculada aún ni cruce con parques nacionales).

Paso 3: Enriquecimiento Geográfico
Determina en qué Provincia o Departamento cae cada incendio (Reverse Geocoding Espacial).
Script: scripts/enrich_location.py
Comando: python scripts/enrich_location.py
Resultado: Columna province completada en fire_events. 

Paso 4: Cálculo de Geometría
Calcula el perímetro (Convex Hull) y la superficie exacta en hectáreas de cada incendio.
Nota: Para incendios pequeños (<3 puntos) genera un buffer circular estimado.
Script: scripts/calculate_area.py
Comando: python scripts/calculate_area.py
Resultado: Columnas perimeter y estimated_area_hectares completadas.

Paso 5: Auditoría Legal (Final)
Cruza los perímetros de incendio con la capa de Áreas Protegidas (Parques Nacionales, Reservas) para determinar prohibiciones de venta (Ley 26.815).
Script: scripts/audit_legal.py
Comando: python scripts/audit_legal.py
Resultado: Tabla fire_protected_area_intersections con detalles del cruce.
Columna is_significant = True en incendios ilegales.
Columna processing_error con etiqueta "ALERTA LEGAL: Afecta [Parque]".

🛠️ Mantenimiento de Tablas Base
Antes de correr el pipeline, asegúrate de que las tablas estáticas estén cargadas.


## Productivo - Cambios en local y envio a produccion
1. PC local → commit + push
2. VM → git pull origin main
3. VM → docker compose up -d --build