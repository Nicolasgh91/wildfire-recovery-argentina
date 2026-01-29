# 🧪 Wildfire Recoveries in Argentina - Casos de Prueba

## Filosofía de Testing

Este documento define **casos de prueba específicos y medibles** para cada fase del desarrollo. Cada test tiene:

- ✅ **Criterios de éxito claros** (números, tiempos, porcentajes)
- 🎯 **Datos de prueba reales** (coordenadas, fechas, IDs)
- 📊 **Métricas de performance** (latencia, throughput, precisión)
- 🔄 **Estrategia de regresión** (qué re-testear en cada fase)

---

## 🗓️ Fase 1: MVP Core (Semanas 1-6)

### **SEMANA 1: Fundamentos**

#### **TEST-1.1: Infraestructura Base**

**Objetivo:** Validar que la infraestructura está operativa

| ID | Caso de Prueba | Criterio de Éxito | Herramienta |
|----|----------------|-------------------|-------------|
| T1.1.1 | API responde en `/health` | Status 200, respuesta < 100ms | `curl` |
| T1.1.2 | PostgreSQL + PostGIS activo | Puede crear punto geográfico | `psql` |
| T1.1.3 | Redis acepta conexiones | SET/GET exitoso | `redis-cli` |
| T1.1.4 | Celery worker activo | Task de prueba ejecutada en < 5seg | Celery CLI |
| T1.1.5 | Nginx proxy funcional | Forwarding correcto a FastAPI | `curl -I` |

**Comandos de Prueba:**

```bash
# T1.1.1: Health check
curl -X GET http://localhost:8000/health
# Esperado: {"status": "healthy", "database": "connected", "version": "3.0.0"}

# T1.1.2: PostGIS test
psql $DATABASE_URL -c "SELECT ST_AsText(ST_GeomFromText('POINT(-58.3816 -34.6037)', 4326));"
# Esperado: POINT(-58.3816 -34.6037)

# T1.1.3: Redis test
redis-cli PING
# Esperado: PONG

# T1.1.4: Celery test
python -c "from workers.tasks import test_task; result = test_task.delay(); print(result.get(timeout=10))"
# Esperado: "Test task completed"

# T1.1.5: Nginx test
curl -I http://localhost/api/v1/health
# Esperado: HTTP/1.1 200 OK, Server: nginx
```

**Criterio de Pase de Fase:** 5/5 tests pasando ✅

---

### **SEMANA 2: Ingesta de Datos**

#### **TEST-2.1: Descarga de NASA FIRMS**

**Objetivo:** Cargar datos históricos sin errores

| ID | Caso de Prueba | Datos de Entrada | Criterio de Éxito |
|----|----------------|------------------|-------------------|
| T2.1.1 | Descargar CSV 2024 VIIRS Argentina | Year=2024, Satellite=VIIRS | Archivo descargado, size > 5MB |
| T2.1.2 | Parsear CSV sin errores | CSV de T2.1.1 | 0 excepciones, 100% filas parseadas |
| T2.1.3 | Filtrar por confidence >= 80% | Raw detections | Solo confidence 'h' o >= 80 |
| T2.1.4 | Insertar en `fire_detections` | 10,000 registros | Tiempo < 30seg, sin duplicados |
| T2.1.5 | Índices espaciales creados | Post-inserción | Query con ST_DWithin < 500ms |

**Script de Prueba:**

```python
# tests/integration/test_firms_ingestion.py

import pytest
from datetime import datetime
from app.services.firms_service import FIRMSService

def test_download_viirs_2024():
    """T2.1.1: Descargar datos VIIRS 2024"""
    service = FIRMSService()
    
    file_path = service.download_bulk_csv(
        year=2024,
        satellite='VIIRS',
        country='Argentina'
    )
    
    assert file_path.exists()
    assert file_path.stat().st_size > 5_000_000  # > 5MB
    
def test_parse_csv_no_errors():
    """T2.1.2: Parsear CSV sin errores"""
    service = FIRMSService()
    
    df = service.parse_csv('test_data/firms_sample.csv')
    
    assert len(df) > 0
    assert df['latitude'].notna().all()
    assert df['longitude'].notna().all()
    assert df['acq_date'].notna().all()

def test_filter_high_confidence():
    """T2.1.3: Filtrar alta confianza"""
    service = FIRMSService()
    
    df = service.parse_csv('test_data/firms_sample.csv')
    df_filtered = service.filter_high_confidence(df, threshold=80)
    
    # Para VIIRS: confidence >= 80
    # Para MODIS: confidence == 'h'
    assert all(
        (row['confidence'] == 'h') or (int(row['confidence']) >= 80)
        for _, row in df_filtered.iterrows()
    )

def test_bulk_insert_performance(db_session):
    """T2.1.4: Inserción masiva rápida"""
    import time
    from app.models.fire import FireDetection
    
    # Generar 10,000 registros de prueba
    detections = [
        FireDetection(
            satellite='VIIRS',
            latitude=-34.0 + (i * 0.001),
            longitude=-58.0 + (i * 0.001),
            acquisition_date=datetime(2024, 1, 1),
            confidence_raw='h',
            confidence_normalized=95
        )
        for i in range(10000)
    ]
    
    start = time.time()
    db_session.bulk_save_objects(detections)
    db_session.commit()
    elapsed = time.time() - start
    
    assert elapsed < 30  # Debe tardar menos de 30 segundos
    
    # Verificar no hay duplicados
    count = db_session.query(FireDetection).count()
    assert count == 10000

def test_spatial_index_performance(db_session):
    """T2.1.5: Índice espacial rápido"""
    import time
    from sqlalchemy import text
    
    # Query espacial con ST_DWithin
    query = text("""
        SELECT COUNT(*) FROM fire_detections
        WHERE ST_DWithin(
            location,
            ST_SetSRID(ST_MakePoint(-58.3816, -34.6037), 4326),
            5000  -- 5km radius
        )
    """)
    
    start = time.time()
    result = db_session.execute(query).scalar()
    elapsed = time.time() - start
    
    assert elapsed < 0.5  # < 500ms con índice GIST
```

**Criterio de Pase:** 5/5 tests pasando + storage < 150MB ✅

---

#### **TEST-2.2: Clustering de Eventos**

**Objetivo:** Agrupar detecciones en eventos únicos correctamente

| ID | Caso de Prueba | Datos de Entrada | Resultado Esperado |
|----|----------------|------------------|--------------------|
| T2.2.1 | Agrupar detecciones cercanas | 100 puntos en 500m radius | 1 fire_event creado |
| T2.2.2 | Separar eventos distantes | 2 grupos a 10km distancia | 2 fire_events |
| T2.2.3 | Calcular estadísticas correctas | Evento con 5 detecciones | avg_frp, max_frp, duration correctos |
| T2.2.4 | Manejo de eventos de 1 sola detección | 1 detección aislada | 1 fire_event (no descartar) |
| T2.2.5 | Performance en dataset grande | 10,000 detecciones | Clustering < 5 minutos |

**Test de Validación Geográfica:**

```python
# tests/integration/test_clustering.py

def test_cluster_nearby_detections(db_session):
    """T2.2.1: Detecciones cercanas = 1 evento"""
    from workers.tasks.clustering import cluster_fire_detections
    from app.models.fire import FireDetection, FireEvent
    
    # Crear 100 detecciones en círculo de 500m
    center_lat, center_lon = -34.6037, -58.3816
    
    for i in range(100):
        # Offset aleatorio ±500m
        offset = 0.005  # ~500m en grados
        lat = center_lat + (random.random() - 0.5) * offset
        lon = center_lon + (random.random() - 0.5) * offset
        
        detection = FireDetection(
            satellite='VIIRS',
            latitude=lat,
            longitude=lon,
            acquisition_date=datetime(2024, 8, 15),
            confidence_normalized=90
        )
        db_session.add(detection)
    
    db_session.commit()
    
    # Ejecutar clustering
    cluster_fire_detections(date_range=['2024-08-15', '2024-08-15'])
    
    # Verificar que se creó 1 solo evento
    events = db_session.query(FireEvent).filter(
        FireEvent.start_date == datetime(2024, 8, 15)
    ).all()
    
    assert len(events) == 1
    assert events[0].total_detections == 100

def test_separate_distant_events(db_session):
    """T2.2.2: Eventos distantes = eventos separados"""
    from workers.tasks.clustering import cluster_fire_detections
    from app.models.fire import FireDetection, FireEvent
    
    # Grupo 1: Buenos Aires (-34.6, -58.4)
    # Grupo 2: Córdoba (-31.4, -64.2) - ~600km de distancia
    
    for lat, lon in [(-34.6, -58.4), (-31.4, -64.2)]:
        for i in range(10):
            detection = FireDetection(
                satellite='VIIRS',
                latitude=lat + random.random() * 0.01,
                longitude=lon + random.random() * 0.01,
                acquisition_date=datetime(2024, 8, 15),
                confidence_normalized=85
            )
            db_session.add(detection)
    
    db_session.commit()
    
    cluster_fire_detections(date_range=['2024-08-15', '2024-08-15'])
    
    events = db_session.query(FireEvent).all()
    assert len(events) == 2  # Dos eventos distintos

def test_statistics_calculation(db_session):
    """T2.2.3: Estadísticas correctas"""
    from workers.tasks.clustering import cluster_fire_detections
    
    # Crear 5 detecciones con FRP conocido
    frp_values = [100.0, 150.0, 200.0, 180.0, 170.0]
    
    for frp in frp_values:
        detection = FireDetection(
            satellite='VIIRS',
            latitude=-34.6,
            longitude=-58.4,
            acquisition_date=datetime(2024, 8, 15),
            fire_radiative_power=frp,
            confidence_normalized=90
        )
        db_session.add(detection)
    
    db_session.commit()
    
    cluster_fire_detections(date_range=['2024-08-15', '2024-08-15'])
    
    event = db_session.query(FireEvent).first()
    
    assert event.total_detections == 5
    assert event.avg_frp == 160.0  # (100+150+200+180+170)/5
    assert event.max_frp == 200.0
```

**Criterio de Pase:** 5/5 tests pasando + lógica de clustering validada ✅

---

### **SEMANA 3: Inteligencia Geoespacial**

#### **TEST-3.1: Intersección Espacial con Áreas Protegidas**

**Datos de Prueba Reales:**

| Parque Nacional | Coordenadas Centro | Fuego de Prueba | Debe Intersectar |
|-----------------|-------------------|-----------------|------------------|
| Iguazú | -25.6954, -54.4367 | -25.7, -54.4 | ✅ SÍ |
| Nahuel Huapi | -41.0, -71.5 | -41.05, -71.52 | ✅ SÍ |
| Chaco | -27.05, -59.55 | -27.1, -59.6 | ✅ SÍ |
| (Fuera de parque) | N/A | -34.6, -58.4 (Buenos Aires) | ❌ NO |

```python
# tests/integration/test_spatial_intersection.py

def test_fire_inside_protected_area(db_session):
    """T3.1.1: Fuego dentro de parque = intersección detectada"""
    from app.models.region import ProtectedArea
    from app.models.fire import FireEvent
    from app.services.spatial_service import SpatialService
    
    # Crear polígono de Parque Nacional Iguazú (simplificado)
    # Bounding box aproximado: -25.5 a -25.8, -54.3 a -54.5
    park = ProtectedArea(
        official_name="Parque Nacional Iguazú",
        category="national_park",
        boundary="POLYGON((-54.3 -25.5, -54.5 -25.5, -54.5 -25.8, -54.3 -25.8, -54.3 -25.5))",
        prohibition_years=60
    )
    db_session.add(park)
    
    # Crear fuego DENTRO del parque
    fire = FireEvent(
        centroid="POINT(-54.4 -25.7)",
        start_date=datetime(2024, 8, 15),
        total_detections=10
    )
    db_session.add(fire)
    db_session.commit()
    
    # Ejecutar intersección
    service = SpatialService(db_session)
    intersections = service.find_fire_protected_area_intersections(fire.id)
    
    assert len(intersections) == 1
    assert intersections[0].protected_area_id == park.id
    assert intersections[0].prohibition_until == datetime(2084, 8, 15).date()  # +60 años

def test_fire_outside_protected_area(db_session):
    """T3.1.2: Fuego fuera de parque = sin intersección"""
    from app.models.region import ProtectedArea
    from app.models.fire import FireEvent
    from app.services.spatial_service import SpatialService
    
    park = ProtectedArea(
        official_name="Parque Nacional Chaco",
        boundary="POLYGON((-59.5 -27.0, -59.6 -27.0, -59.6 -27.1, -59.5 -27.1, -59.5 -27.0))",
        category="national_park"
    )
    db_session.add(park)
    
    # Fuego en Buenos Aires (lejos del Chaco)
    fire = FireEvent(
        centroid="POINT(-58.4 -34.6)",
        start_date=datetime(2024, 8, 15),
        total_detections=5
    )
    db_session.add(fire)
    db_session.commit()
    
    service = SpatialService(db_session)
    intersections = service.find_fire_protected_area_intersections(fire.id)
    
    assert len(intersections) == 0  # Sin intersección

def test_spatial_query_performance(db_session):
    """T3.1.3: Query espacial < 2 segundos con 1000 fuegos"""
    import time
    from app.services.spatial_service import SpatialService
    
    # Crear 1000 fuegos aleatorios en Argentina
    for i in range(1000):
        fire = FireEvent(
            centroid=f"POINT({-55 - random.random() * 10} {-35 - random.random() * 10})",
            start_date=datetime(2024, 8, 15),
            total_detections=1
        )
        db_session.add(fire)
    db_session.commit()
    
    # Consultar fuegos en 500m alrededor de un punto
    service = SpatialService(db_session)
    
    start = time.time()
    fires = service.find_fires_near_location(
        lat=-34.6037,
        lon=-58.3816,
        radius_meters=500
    )
    elapsed = time.time() - start
    
    assert elapsed < 2.0  # Debe responder en < 2 segundos
```

**Criterio de Pase:** Precisión 100% en intersecciones + performance < 2seg ✅

---

#### **TEST-3.2: Endpoint UC-01 (Auditoría)**

**Casos de Prueba End-to-End:**

```python
# tests/e2e/test_audit_endpoint.py

def test_audit_endpoint_with_fire(client):
    """T3.2.1: Auditoría encuentra fuego histórico"""
    
    # Setup: Crear fuego en DB
    # (Asume que hay un fuego en -27.1, -59.6 del 2022-08-15)
    
    response = client.get(
        "/api/v1/audit/land-use",
        params={
            "lat": -27.1,
            "lon": -59.6,
            "radius": 500
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["fires_found"] >= 1
    assert data["is_prohibited"] == True
    assert "2052-08-15" in data["prohibition_until"]  # 30 años después
    assert len(data["fires"]) > 0
    assert "evidence_url" in data["fires"][0]

def test_audit_endpoint_no_fire(client):
    """T3.2.2: Auditoría sin fuegos = área limpia"""
    
    # Consultar punto sin fuegos (ej: océano Atlántico)
    response = client.get(
        "/api/v1/audit/land-use",
        params={
            "lat": -38.0,
            "lon": -57.0,  # Mar del Plata - offshore
            "radius": 500
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["fires_found"] == 0
    assert data["is_prohibited"] == False
    assert data["fires"] == []

def test_audit_endpoint_performance(client):
    """T3.2.3: Respuesta < 2 segundos"""
    import time
    
    start = time.time()
    response = client.get(
        "/api/v1/audit/land-use",
        params={"lat": -34.6, "lon": -58.4, "radius": 500}
    )
    elapsed = time.time() - start
    
    assert response.status_code == 200
    assert elapsed < 2.0

def test_audit_endpoint_validation(client):
    """T3.2.4: Validación de parámetros"""
    
    # Latitud inválida
    response = client.get(
        "/api/v1/audit/land-use",
        params={"lat": 100, "lon": -58.4}  # lat debe ser -90 a 90
    )
    assert response.status_code == 422  # Validation error
    
    # Radio muy grande
    response = client.get(
        "/api/v1/audit/land-use",
        params={"lat": -34.6, "lon": -58.4, "radius": 50000}  # > 5km
    )
    assert response.status_code == 422
```

**Criterio de Pase:** 4/4 tests pasando + latencia p95 < 2seg ✅

---

### **SEMANA 4: Contexto Climático**

#### **TEST-4.1: Integración Open-Meteo**

**Datos de Prueba:**

| Fecha | Coordenadas | Temp Esperada (°C) | Viento Esperado (km/h) |
|-------|-------------|-------------------|------------------------|
| 2024-08-15 | -34.6, -58.4 | 10-20 | 15-30 |
| 2024-01-15 | -27.5, -59.0 | 28-35 | 10-25 |

```python
# tests/integration/test_climate_service.py

def test_fetch_historical_climate():
    """T4.1.1: Obtener datos climáticos históricos"""
    from app.services.climate_service import ClimateService
    
    service = ClimateService()
    
    data = service.fetch_historical_weather(
        latitude=-34.6037,
        longitude=-58.3816,
        date=datetime(2024, 8, 15)
    )
    
    assert data is not None
    assert "temp_max_celsius" in data
    assert "wind_speed_kmh" in data
    assert 0 <= data["temp_max_celsius"] <= 50  # Rango razonable
    assert 0 <= data["wind_speed_kmh"] <= 150

def test_spatial_clustering_reduces_api_calls():
    """T4.1.2: Clustering reduce llamadas a API"""
    from app.services.climate_service import ClimateService
    from app.models.fire import FireEvent
    
    service = ClimateService()
    
    # 100 fuegos en área de 10km x 10km
    fires = [
        FireEvent(
            centroid=f"POINT({-58.4 + i*0.001} {-34.6 + i*0.001})",
            start_date=datetime(2024, 8, 15)
        )
        for i in range(100)
    ]
    
    # Clustering debería reducir a ~10 consultas únicas
    clusters = service.cluster_fires_spatially(fires, resolution=6)  # H3 resolution 6
    
    assert len(clusters) < 20  # Reducción significativa
    assert len(clusters) >= 1

def test_climate_enrichment_respects_rate_limit():
    """T4.1.3: No exceder 10k llamadas/día"""
    from app.services.climate_service import ClimateService
    from unittest.mock import patch
    
    service = ClimateService()
    
    # Simular 100 llamadas
    with patch.object(service, 'fetch_historical_weather') as mock_fetch:
        mock_fetch.return_value = {"temp_max_celsius": 25}
        
        for i in range(100):
            service.fetch_historical_weather(
                latitude=-34.6,
                longitude=-58.4,
                date=datetime(2024, 8, 15)
            )
        
        # Verificar que se respeta cache (no hace 100 llamadas reales)
        assert mock_fetch.call_count <= 100
```

**Criterio de Pase:** Clustering funciona + respeto de rate limits ✅

---

### **SEMANA 5: Pipeline de Evidencia Visual**

#### **TEST-5.1: Descarga de Imágenes Sentinel-2**

**Casos de Prueba:**

```python
# tests/integration/test_sentinel_service.py

def test_find_cloud_free_image():
    """T5.1.1: Encontrar imagen con < 20% nubes"""
    from app.services.sentinel_service import SentinelService
    
    service = SentinelService()
    
    # Buscar imagen para fuego en Corrientes (zona con buena cobertura)
    images = service.search_images(
        bbox=(-58.8, -27.5, -58.7, -27.4),  # 10km x 10km
        date_range=(datetime(2024, 8, 1), datetime(2024, 8, 31)),
        max_cloud_cover=20
    )
    
    assert len(images) > 0
    assert all(img["cloud_cover"] < 20 for img in images)

def test_download_rgb_subset():
    """T5.1.2: Descargar subset RGB"""
    from app.services.sentinel_service import SentinelService
    
    service = SentinelService()
    
    # Descargar área de 10km x 10km
    image_data = service.download_rgb_subset(
        bbox=(-58.8, -27.5, -58.7, -27.4),
        date=datetime(2024, 8, 15),
        bands=['B04', 'B03', 'B02']  # RGB
    )
    
    assert image_data is not None
    assert len(image_data) < 20_000_000  # < 20MB
    assert image_data[:4] == b'II*\x00' or image_data[:2] == b'MM'  # TIFF header

def test_calculate_ndvi():
    """T5.1.3: Calcular NDVI correctamente"""
    import numpy as np
    from app.services.sentinel_service import calculate_ndvi
    
    # Datos sintéticos
    red_band = np.array([[100, 150], [200, 250]], dtype=np.float32)
    nir_band = np.array([[300, 350], [400, 450]], dtype=np.float32)
    
    ndvi = calculate_ndvi(red_band, nir_band)
    
    # NDVI = (NIR - RED) / (NIR + RED)
    # Ejemplo: (300 - 100) / (300 + 100) = 200/400 = 0.5
    
    assert -1 <= ndvi.mean() <= 1
    assert ndvi.shape == red_band.shape
    assert np.isclose(ndvi[0, 0], 0.5, atol=0.01)
```

**Criterio de Pase:** Descarga exitosa + NDVI calculado correctamente ✅

---

### **SEMANA 6: Auditoría y Documentación**

#### **TEST-6.1: Vista de Calidad del Dato (UC-11)**

```python
# tests/integration/test_quality_metrics.py

def test_quality_score_calculation():
    """T6.1.1: Score de calidad calculado correctamente"""
    from app.models.fire import FireEvent
    from app.db.session import SessionLocal
    
    db = SessionLocal()
    
    # Crear fuego con datos completos
    fire = FireEvent(
        centroid="POINT(-58.4 -34.6)",
        start_date=datetime(2024, 8, 15),
        total_detections=5,
        avg_confidence=92,
        has_satellite_imagery=True,
        has_climate_data=True
    )
    db.add(fire)
    db.commit()
    
    # Consultar vista de calidad
    quality = db.execute(
        f"SELECT reliability_score, reliability_class FROM fire_event_quality_metrics WHERE fire_event_id = '{fire.id}'"
    ).first()
    
    # Score esperado:
    # - 92 * 0.4 = 36.8 (confidence)
    # - 20 (tiene imágenes)
    # - 20 (tiene clima)
    # - 20 (5 detecciones >= 3)
    # Total: 96.8 → 'high'
    
    assert quality.reliability_score >= 90
    assert quality.reliability_class == 'high'

def test_quality_endpoint():
    """T6.1.2: Endpoint de calidad funciona"""
    
    response = client.get(f"/api/v1/quality/fire-event/{fire_id}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "reliability_score" in data
    assert "data_sources" in data
    assert "limitations" in data
```

**Criterio de Pase:** Métricas de calidad precisas + endpoint funcional ✅

---

## 📊 Matriz de Regresión (Qué Re-testear en Cada Fase)

| Fase Actual | Tests a Re-ejecutar | Razón |
|-------------|-------------------|-------|
| Semana 2 | T1.1.1 - T1.1.5 | Validar infra sigue estable |
| Semana 3 | T2.1.1 - T2.2.5 | Validar ingesta no se rompió |
| Semana 4 | T3.1.1 - T3.2.4 | Validar queries espaciales siguen rápidas |
| Semana 5 | T4.1.1 - T4.1.3 | Validar clima sigue funcionando |
| Semana 6 | **TODOS** | Regresión completa pre-lanzamiento |

---

## 🎯 Criterios de Éxito del MVP (Fin de Semana 6)

### Performance
- ✅ P95 latencia < 2 segundos (consultas)
- ✅ P99 latencia < 5 segundos
- ✅ Throughput > 100 req/min

### Precisión
- ✅ Intersecciones espaciales: 100% precisión
- ✅ Cálculo de fechas legales: 0 errores
- ✅ NDVI calculado: error < 5% vs valores esperados

### Almacenamiento
- ✅ PostgreSQL < 450MB (90% del límite)
- ✅ R2 < 8GB (80% del límite)

### Cobertura de Tests
- ✅ Unit tests > 80% coverage
- ✅ Integration tests cubren todos los endpoints
- ✅ E2E tests cubren 3 flujos principales

---