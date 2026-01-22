"""
Microservicio de Análisis de Imágenes Satelitales
Servicio independiente para procesamiento de imágenes y análisis temporal
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional, Dict
import json
import ee

from image_service.config import settings
from image_service.gee_client import GEEClient
from image_service.analyzers.ndvi import NDVIAnalyzer
from image_service.analyzers.construcciones import ConstruccionesDetector

# Importar cliente de Supabase (reutilizamos desde api)
from supabase import create_client, Client

# ========== MODELOS ==========

class AnalisisRequest(BaseModel):
    """Request para iniciar análisis de un incendio"""
    incendio_id: str
    latitud: float
    longitud: float
    fecha_incendio: str  # YYYY-MM-DD
    area_hectareas: Optional[float] = None
    forzar_reanalisis: bool = False


class AnalisisResponse(BaseModel):
    """Response del análisis"""
    incendio_id: str
    estado: str
    mensaje: str
    meses_analizados: int = 0
    meses_totales: int = 36


# ========== INICIALIZAR APP ==========

app = FastAPI(
    title=settings.service_name,
    version=settings.service_version,
    description="Microservicio para análisis temporal de imágenes satelitales post-incendio"
)

# Cliente de Supabase (para guardar resultados)
supabase: Client = create_client(
    settings.supabase_url,
    settings.supabase_service_key
)

# Inicializar GEE
gee_client = GEEClient()
ndvi_analyzer = NDVIAnalyzer()
construcciones_detector = ConstruccionesDetector()


# ========== FUNCIONES AUXILIARES ==========

def obtener_incendio_bd(incendio_id: str) -> Optional[Dict]:
    """Obtiene datos del incendio desde BD"""
    response = supabase.table('incendios') \
        .select('*') \
        .eq('id', incendio_id) \
        .execute()
    
    return response.data[0] if response.data else None


def actualizar_estado_incendio(incendio_id: str, estado: str, error: str = None):
    """Actualiza estado del incendio en BD"""
    update_data = {'estado_analisis': estado}
    if error:
        update_data['error_mensaje'] = error
    
    supabase.table('incendios') \
        .update(update_data) \
        .eq('id', incendio_id) \
        .execute()


def guardar_analisis_mensual(analisis_data: Dict):
    """Guarda análisis mensual en BD"""
    try:
        supabase.table('analisis_mensual') \
            .insert(analisis_data) \
            .execute()
    except Exception as e:
        # Si ya existe (unique constraint), actualizar
        supabase.table('analisis_mensual') \
            .update(analisis_data) \
            .eq('incendio_id', analisis_data['incendio_id']) \
            .eq('mes_numero', analisis_data['mes_numero']) \
            .execute()


def analizar_incendio_completo(
    incendio_id: str,
    latitud: float,
    longitud: float,
    fecha_incendio: datetime
):
    """
    Analiza un incendio completo (36 meses)
    Se ejecuta en background
    """
    try:
        # Marcar como procesando
        actualizar_estado_incendio(incendio_id, 'procesando')
        
        meses_exitosos = 0
        
        # Iterar 36 meses
        for mes in range(1, settings.meses_analisis + 1):
            try:
                # Calcular fecha objetivo (mes X después del incendio)
                fecha_objetivo = fecha_incendio + timedelta(days=30 * mes)
                
                # Si la fecha objetivo es futura, detener
                if fecha_objetivo > datetime.now():
                    break
                
                # Calcular NDVI
                ndvi_resultado = ndvi_analyzer.calcular_ndvi_mes(
                    latitud=latitud,
                    longitud=longitud,
                    fecha_objetivo=fecha_objetivo
                )
                
                # Si no hay imagen disponible, continuar al siguiente mes
                if not ndvi_resultado:
                    continue
                
                # Detectar construcciones (comparar con mes anterior si existe)
                construcciones = False
                if mes > 1:
                    fecha_anterior = fecha_incendio + timedelta(days=30 * (mes - 1))
                    cambios = construcciones_detector.detectar_cambios(
                        latitud=latitud,
                        longitud=longitud,
                        fecha_antes=fecha_anterior,
                        fecha_despues=fecha_objetivo
                    )
                    construcciones = cambios.get('construcciones_detectadas', False)
                
                # Calcular porcentaje de recuperación
                porcentaje_recuperacion = ndvi_analyzer.calcular_porcentaje_recuperacion(
                    ndvi_actual=ndvi_resultado['ndvi_promedio']
                )
                
                # Preparar datos para BD
                analisis_data = {
                    'incendio_id': incendio_id,
                    'mes_numero': mes,
                    'fecha_imagen': ndvi_resultado['fecha_imagen'],
                    'ndvi_promedio': ndvi_resultado['ndvi_promedio'],
                    'ndvi_min': ndvi_resultado['ndvi_min'],
                    'ndvi_max': ndvi_resultado['ndvi_max'],
                    'ndvi_desviacion': ndvi_resultado['ndvi_desviacion'],
                    'construcciones_detectadas': construcciones,
                    'porcentaje_recuperacion': porcentaje_recuperacion,
                    'calidad_imagen': ndvi_resultado['calidad_imagen'],
                    'nubosidad_porcentaje': ndvi_resultado['nubosidad_porcentaje'],
                    'notas': f"Análisis automático - {ndvi_analyzer.interpretar_ndvi(ndvi_resultado['ndvi_promedio'])}"
                }
                
                # Guardar en BD
                guardar_analisis_mensual(analisis_data)
                meses_exitosos += 1
                
                print(f"✓ Incendio {incendio_id[:8]}... - Mes {mes}/36 completado")
            
            except Exception as e:
                print(f"✗ Error en mes {mes}: {str(e)}")
                continue
        
        # Marcar como completado
        actualizar_estado_incendio(incendio_id, 'completado')
        print(f"✓ Análisis completo: {meses_exitosos}/36 meses procesados")
    
    except Exception as e:
        # Marcar como error
        actualizar_estado_incendio(incendio_id, 'error', str(e))
        print(f"✗ Error fatal en análisis: {str(e)}")


# ========== ENDPOINTS ==========

@app.get("/", tags=["General"])
async def root():
    """Endpoint raíz"""
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "status": "online",
        "capabilities": [
            "Análisis NDVI mensual",
            "Detección de construcciones",
            "Análisis temporal 36 meses"
        ]
    }


@app.get("/health", tags=["General"])
async def health():
    """Health check del microservicio"""
    gee_status = gee_client.test_connection()
    
    return {
        "status": "healthy" if gee_status["status"] == "success" else "degraded",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "gee": gee_status["status"],
            "database": "ok"
        }
    }


@app.post("/analizar", response_model=AnalisisResponse, tags=["Análisis"])
async def iniciar_analisis(
    request: AnalisisRequest,
    background_tasks: BackgroundTasks
):
    """
    Inicia análisis temporal de un incendio (36 meses)
    
    El análisis se ejecuta en background y puede tardar varios minutos.
    El endpoint retorna inmediatamente con el estado inicial.
    
    Consulta el estado en la API principal: GET /incendios/{id}
    """
    # Verificar que el incendio existe en BD
    incendio = obtener_incendio_bd(request.incendio_id)
    if not incendio:
        raise HTTPException(
            status_code=404,
            detail=f"Incendio {request.incendio_id} no encontrado"
        )
    
    # Verificar si ya está en proceso o completado
    if incendio['estado_analisis'] == 'completado' and not request.forzar_reanalisis:
        return AnalisisResponse(
            incendio_id=request.incendio_id,
            estado='ya_completado',
            mensaje='El análisis ya fue completado. Use forzar_reanalisis=true para reanalizar',
            meses_analizados=36,
            meses_totales=36
        )
    
    if incendio['estado_analisis'] == 'procesando':
        return AnalisisResponse(
            incendio_id=request.incendio_id,
            estado='en_proceso',
            mensaje='El análisis ya está en proceso',
            meses_analizados=0,
            meses_totales=36
        )
    
    # Parsear fecha
    fecha_incendio = datetime.strptime(request.fecha_incendio, '%Y-%m-%d')
    
    # Lanzar análisis en background
    background_tasks.add_task(
        analizar_incendio_completo,
        incendio_id=request.incendio_id,
        latitud=request.latitud,
        longitud=request.longitud,
        fecha_incendio=fecha_incendio
    )
    
    return AnalisisResponse(
        incendio_id=request.incendio_id,
        estado='iniciado',
        mensaje='Análisis iniciado en background. Consulte el estado en /incendios/{id}',
        meses_analizados=0,
        meses_totales=36
    )


@app.post("/analizar/mes", tags=["Análisis"])
async def analizar_mes_unico(
    incendio_id: str,
    latitud: float,
    longitud: float,
    fecha: str,
    mes_numero: int
):
    """
    Analiza un mes específico (para testing o reanalizar meses puntuales)
    """
    fecha_obj = datetime.strptime(fecha, '%Y-%m-%d')
    
    # Calcular NDVI
    ndvi_resultado = ndvi_analyzer.calcular_ndvi_mes(
        latitud=latitud,
        longitud=longitud,
        fecha_objetivo=fecha_obj
    )
    
    if not ndvi_resultado:
        raise HTTPException(
            status_code=404,
            detail="No se encontraron imágenes para la fecha especificada"
        )
    
    return {
        "incendio_id": incendio_id,
        "mes_numero": mes_numero,
        "ndvi": ndvi_resultado,
        "interpretacion": ndvi_analyzer.interpretar_ndvi(ndvi_resultado['ndvi_promedio'])
    }


# ========== INICIAR SERVIDOR ==========

if __name__ == "__main__":
    import uvicorn
    
    print(f"\n{'='*60}")
    print(f"🛰️  {settings.service_name} v{settings.service_version}")
    print(f"{'='*60}")
    print(f"📍 URL: http://{settings.service_host}:{settings.service_port}")
    print(f"📚 Docs: http://{settings.service_host}:{settings.service_port}/docs")
    print(f"{'='*60}\n")
    
    uvicorn.run(
        "image_service.main:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=settings.debug
    )