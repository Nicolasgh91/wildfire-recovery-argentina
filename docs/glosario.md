# 📚 Glosario ForestGuard

Este documento define términos clave técnicos, conceptos de teledetección y terminología de dominio utilizada en toda la plataforma ForestGuard.

## 🛰️ Teledetección y fuentes de datos

### NASA FIRMS
**Fire Information for Resource Management System**. Un programa de la NASA que distribuye datos de incendios casi en tiempo real de los sensores MODIS y VIIRS.
- **Uso**: Detección inicial de anomalías térmicas (focos de calor).

### VIIRS
**Visible Infrared Imaging Radiometer Suite**. Un sensor a bordo de los satélites Suomi NPP y NOAA-20.
- **Resolución**: 375m (alta resolución).
- **Ventaja**: Mejor detección de incendios pequeños que MODIS.

### MODIS
**Moderate Resolution Imaging Spectroradiometer**. Instrumento clave a bordo de los satélites Terra y Aqua.
- **Resolución**: 1km.
- **Ventaja**: Larga historia de registros (desde el año 2000).

### Sentinel-2
Misión de imágenes multiespectrales de alta resolución y amplio barrido del programa Copernicus de la ESA (Agencia Espacial Europea).
- **Resolución**: 10m - 20m.
- **Uso**: Análisis detallado de vegetación, mapeo de áreas quemadas y clasificación de uso del suelo.
- **Frecuencia de visita**: ~5 días.

### GEE (Google Earth Engine)
Plataforma de análisis geoespacial en la nube que permite analizar imágenes satelitales a escala planetaria.
- **Rol**: Realiza cálculos del lado del servidor de NDVI y procesamiento de imágenes sin descargar conjuntos de datos masivos.

### NDVI
**Normalized Difference Vegetation Index** (Índice de Vegetación de Diferencia Normalizada). Una métrica utilizada para cuantificar la salud y densidad de la vegetación.
- **Fórmula**: `(NIR - Red) / (NIR + Red)`
- **Rango**: -1 a +1.
  - `> 0.5`: Vegetación densa/saludable.
  - `0.1 - 0.2`: Suelo desnudo.
  - `< 0`: Agua o no vegetado.
- **Uso**: Monitoreo de recuperación post-incendio y detección de desmonte ilegal.

---

## 🏗️ Arquitectura técnica

### PostGIS
Extensión de base de datos espacial para PostgreSQL.
- **Rol**: Almacena todos los datos geoespaciales (eventos de incendio, áreas protegidas) y realiza consultas espaciales (ej., "Encontrar todos los incendios a menos de 500m de este punto").

### Cloudflare R2
Servicio de almacenamiento de objetos compatible con S3 de Cloudflare.
- **Rol**: Almacena artefactos generados como miniaturas de mapas, reportes PDF y certificados.
- **Ventaja**: Cero costos de egreso (ancho de banda gratuito).

### Redis
Almacén de estructura de datos en memoria.
- **Rol**: Actúa como broker de mensajes para Celery, gestionando colas para tareas asíncronas en segundo plano (ej., "descargar_imágenes").

### Celery
Cola de tareas distribuida para Python.
- **Rol**: Maneja procesos pesados en segundo plano (ingesta, análisis de imágenes) para mantener la API rápida y receptiva.

### H3
Sistema de indexación geoespacial jerárquico hexagonal.
- **Rol**: Utilizado para agrupar detecciones de incendios en "Eventos de Incendio" significativos basados en proximidad espacial.

---

## 🌲 Conceptos de dominio

### Evento de incendio (Fire Event)
Entidad consolidada que representa un incendio forestal, derivada de agrupar múltiples detecciones satelitales individuales (focos de calor) en espacio y tiempo. A diferencia de una detección cruda, un "Evento de Incendio" tiene fecha de inicio, fecha de fin, área estimada y duración total.

### Auditoría de uso del suelo (UC-01)
Proceso de verificación formal para comprobar si una parcela específica de tierra intersecta con eventos de incendio históricos. Utilizado por profesionales legales para determinar si aplican "prohibiciones de fuego" (Ley de Manejo del Fuego) a una propiedad.

### VAE (Vegetation Analysis Engine)
Servicio interno (worker) responsable de analizar imágenes Satellite-2 para rastrear la recuperación de vegetación (NDVI) y marcar anomalías (ej., limpieza inesperada en un área en recuperación).

### ERS (Evidence Reporting Service)
Servicio interno que agrega datos de la BD, GEE y APIs climáticas para generar documentos legalmente robustos (PDFs) y paquetes de evidencia.

### Hash del certificado
Firma criptográfica (SHA-256) agregada a cada certificado PDF generado por ForestGuard. Esto permite a cualquiera verificar que el documento no ha sido manipulado escaneando el código QR o comprobando el hash contra la API.

### Área protegida
Tierra legalmente designada (Parques Nacionales, Reservas) donde la actividad humana está restringida. Los incendios en estas áreas activan alertas especiales de alta prioridad y prohibiciones permanentes de cambio de uso.
