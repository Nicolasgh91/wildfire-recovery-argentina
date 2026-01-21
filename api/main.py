"""
API Principal - Wildfire Recovery System
FastAPI application para consultar y analizar incendios
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import List, Optional

from api.config import settings
from api.database import db
from api.models import (
    DetectarIncendiosRequest,
    CrearIncendioRequest,
    IncendioResponse,
    IncendioDetalleResponse,
    EstadisticasResponse,
    HealthCheckResponse,
    ErrorResponse
)

# ========== INICIALIZAR APP ==========

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API para monitoreo de recuperación de terrenos afectados por incendios forestales",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS (permitir requests desde cualquier origen)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== ENDPOINTS ==========

@app.get("/", tags=["General"])
async def root():
    """Endpoint raíz con información de la API"""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "online",
        "docs": "/docs",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health", response_model=HealthCheckResponse, tags=["General"])
async def health_check():
    """
    Health check - Verifica estado de servicios
    """
    # Verificar conexión a BD
    db_status = db.test_connection()
    
    # Verificar conexión a GEE (importamos aquí para no cargar siempre)
    try:
        from image_service.gee_client import GEEClient
        gee_client = GEEClient()
        gee_status = gee_client.test_connection()
    except Exception as e:
        gee_status = {"status": "error", "message": str(e)}
    
    # Determinar estado general
    all_ok = (
        db_status["status"] == "success" and
        gee_status["status"] == "success"
    )
    
    return {
        "status": "healthy" if all_ok else "degraded",
        "timestamp": datetime.now(),
        "services": {
            "database": db_status["status"],
            "gee": gee_status["status"]
        }
    }


@app.get("/estadisticas", response_model=EstadisticasResponse, tags=["Estadísticas"])
async def obtener_estadisticas():
    """
    Obtiene estadísticas generales del sistema
    """
    stats = db.estadisticas_generales()
    return stats


@app.get("/incendios", response_model=List[IncendioResponse], tags=["Incendios"])
async def listar_incendios(
    provincia: Optional[str] = Query(None, description="Filtrar por provincia"),
    fecha_inicio: Optional[str] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: Optional[str] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    tipo: Optional[str] = Query(None, description="Tipo: nuevo o recurrente"),
    limite: int = Query(100, ge=1, le=settings.max_incendios_por_consulta)
):
    """
    Lista incendios con filtros opcionales
    
    - **provincia**: Filtrar por provincia (ej: "Buenos Aires")
    - **fecha_inicio**: Filtrar desde fecha (ej: "2023-01-01")
    - **fecha_fin**: Filtrar hasta fecha (ej: "2023-12-31")
    - **tipo**: Filtrar por tipo ("nuevo" o "recurrente")
    - **limite**: Máximo número de resultados (default: 100)
    """
    incendios = db.listar_incendios(
        provincia=provincia,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        tipo=tipo,
        limite=limite
    )
    
    return incendios


@app.get("/incendios/{incendio_id}", response_model=IncendioDetalleResponse, tags=["Incendios"])
async def obtener_incendio(incendio_id: str):
    """
    Obtiene detalles completos de un incendio
    
    Incluye:
    - Datos básicos del incendio
    - Análisis mensuales (36 meses)
    - Superposiciones con otros incendios
    """
    # Obtener incendio
    incendio = db.obtener_incendio(incendio_id)
    if not incendio:
        raise HTTPException(
            status_code=404,
            detail=f"Incendio {incendio_id} no encontrado"
        )
    
    # Obtener análisis mensuales
    analisis = db.obtener_analisis_incendio(incendio_id)
    
    # Obtener superposiciones
    superposiciones = db.obtener_superposiciones_incendio(incendio_id)
    
    return {
        "incendio": incendio,
        "analisis_mensual": analisis,
        "superposiciones": superposiciones
    }


@app.post("/incendios", response_model=IncendioResponse, tags=["Incendios"], status_code=201)
async def crear_incendio(request: CrearIncendioRequest):
    """
    Crea un nuevo incendio manualmente
    
    El sistema automáticamente:
    - Detecta si es recurrente (< 100m de otro incendio, > 6 meses después)
    - Detecta superposiciones (> 5% de área compartida)
    """
    # Preparar datos para insertar
    incendio_data = {
        "fecha_deteccion": request.fecha_deteccion.isoformat(),
        "provincia": request.provincia,
        "localidad": request.localidad,
        "latitud": request.latitud,
        "longitud": request.longitud,
        "area_afectada_hectareas": request.area_afectada_hectareas,
        # El trigger detectará automáticamente si es recurrente
        # y calculará superposiciones
    }
    
    try:
        incendio = db.crear_incendio(incendio_data)
        return incendio
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error creando incendio: {str(e)}"
        )


@app.post("/incendios/detectar", tags=["Incendios"])
async def detectar_incendios(request: DetectarIncendiosRequest):
    """
    Detecta incendios usando Google Earth Engine
    
    **NOTA:** Este endpoint está en desarrollo.
    Actualmente retorna metadata sobre imágenes disponibles.
    En producción, procesará y guardará incendios automáticamente.
    """
    try:
        from image_service.gee_client import GEEClient
        gee_client = GEEClient()
        resultado = gee_client.detectar_incendios(
            provincia=request.provincia,
            fecha_inicio=request.fecha_inicio.isoformat(),
            fecha_fin=request.fecha_fin.isoformat(),
            umbral_confianza=request.umbral_confianza
        )
        
        return {
            "status": "success",
            "mensaje": "Detección de incendios completada",
            "resultado": resultado
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error detectando incendios: {str(e)}"
        )


# ========== INICIAR SERVIDOR ==========

if __name__ == "__main__":
    import uvicorn
    
    print(f"\n{'='*60}")
    print(f"🔥 {settings.app_name} v{settings.app_version}")
    print(f"{'='*60}")
    print(f"📍 URL: http://{settings.api_host}:{settings.api_port}")
    print(f"📚 Docs: http://{settings.api_host}:{settings.api_port}/docs")
    print(f"{'='*60}\n")
    
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )