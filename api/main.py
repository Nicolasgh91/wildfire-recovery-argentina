"""
API Principal - Wildfire Recovery System
FastAPI application para consultar y analizar incendios
"""
from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import List, Optional
import pandas as pd
import io
import time  # <--- NUEVO: Para manejar pausas entre lotes

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
    incendio = db.obtener_incendio(incendio_id)
    if not incendio:
        raise HTTPException(
            status_code=404,
            detail=f"Incendio {incendio_id} no encontrado"
        )
    
    analisis = db.obtener_analisis_incendio(incendio_id)
    superposiciones = db.obtener_superposiciones_incendio(incendio_id)
    
    return {
        "incendio": incendio,
        "analisis_mensual": analisis,
        "superposiciones": superposiciones
    }


@app.post("/incendios", response_model=IncendioResponse, tags=["Incendios"], status_code=201)
async def crear_incendio(request: CrearIncendioRequest):
    incendio_data = {
        "fecha_deteccion": request.fecha_deteccion.isoformat(),
        "provincia": request.provincia,
        "localidad": request.localidad,
        "latitud": request.latitud,
        "longitud": request.longitud,
        "area_afectada_hectareas": request.area_afectada_hectareas,
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


@app.post("/incendios/importar", tags=["Incendios"])
async def importar_incendios_csv(archivo: UploadFile = File(..., description="Archivo CSV con incendios procesados")):
    """
    Importa incendios procesados desde un archivo CSV con control de lotes y logs.
    """
    # Validar que sea un archivo CSV
    if not archivo.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="El archivo debe ser un CSV (.csv)"
        )
    
    try:
        # Leer el contenido del archivo
        print(f"\n📥 Recibiendo archivo: {archivo.filename}...") # LOG
        contenido = await archivo.read()
        df = pd.read_csv(io.BytesIO(contenido))
        print(f"📊 CSV Leído. Filas totales: {len(df)}") # LOG
        
        # Validar columnas requeridas
        columnas_requeridas = ['latitud', 'longitud', 'fecha_primera_deteccion', 'area_hectareas']
        columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
        
        if columnas_faltantes:
            raise HTTPException(
                status_code=400,
                detail=f"Faltan columnas requeridas: {', '.join(columnas_faltantes)}"
            )
        
        # Preparar datos para inserción
        incendios_para_insertar = []
        errores = []
        
        print("🛠️ Procesando filas y generando geometrías...") # LOG

        for idx, row in df.iterrows():
            try:
                # Mapear columnas del CSV a campos de la BD
                incendio_data = {
                    'fecha_deteccion': pd.to_datetime(row['fecha_primera_deteccion']).date().isoformat(),
                    'latitud': float(row['latitud']),
                    'longitud': float(row['longitud']),
                    'area_afectada_hectareas': float(row['area_hectareas']) if pd.notna(row['area_hectareas']) else None,
                }
                
                # Agregar provincia y localidad si existen
                if 'provincia' in df.columns and pd.notna(row.get('provincia')):
                    incendio_data['provincia'] = str(row['provincia'])
                
                if 'localidad' in df.columns and pd.notna(row.get('localidad')):
                    incendio_data['localidad'] = str(row['localidad'])
                
                # Crear geometría
                try:
                    if all(col in df.columns and pd.notna(row.get(col)) for col in ['lat_min', 'lat_max', 'lon_min', 'lon_max']):
                        lat_min = float(row['lat_min'])
                        lat_max = float(row['lat_max'])
                        lon_min = float(row['lon_min'])
                        lon_max = float(row['lon_max'])
                        wkt = f"SRID=4326;POLYGON(({lon_min} {lat_min}, {lon_max} {lat_min}, {lon_max} {lat_max}, {lon_min} {lat_max}, {lon_min} {lat_min}))"
                        incendio_data['geometria'] = wkt
                    else:
                        wkt = f"SRID=4326;POINT({incendio_data['longitud']} {incendio_data['latitud']})"
                        incendio_data['geometria'] = wkt
                except Exception:
                    pass
                
                incendio_data['estado_analisis'] = 'pendiente'
                incendios_para_insertar.append(incendio_data)
                
            except Exception as e:
                errores.append({
                    'fila': idx + 2,
                    'error': str(e)
                })
        
        if not incendios_para_insertar:
            raise HTTPException(status_code=400, detail="No se pudo procesar ningún incendio del CSV")
        
        # --- INICIO DE INSERCIÓN POR LOTES (MODIFICADO) ---
        lote_size = 1000 # Reducido a 1000 para evitar Timeouts
        total_rows = len(incendios_para_insertar)
        total_insertados = 0
        
        print(f"🚀 Iniciando inserción de {total_rows} registros en la Base de Datos...") # LOG
        
        for i in range(0, total_rows, lote_size):
            lote = incendios_para_insertar[i:i + lote_size]
            
            # Calcular progreso para mostrar en consola
            batch_num = (i // lote_size) + 1
            total_batches = (total_rows // lote_size) + (1 if total_rows % lote_size != 0 else 0)
            percent = round((i / total_rows) * 100, 1)
            
            print(f"⏳ Insertando lote {batch_num}/{total_batches} ({percent}%)... ", end="", flush=True) # LOG
            
            try:
                resultado = db.crear_incendios_batch(lote)
                count = len(resultado)
                total_insertados += count
                print(f"✅ OK ({count} inc.)") # LOG OK
                
                # PAUSA ESTRATÉGICA: Dar respiro a la DB para procesar triggers
                time.sleep(0.2) 
                
            except Exception as e:
                print(f"❌ ERROR: {str(e)}") # LOG ERROR
                errores.append({
                    'lote': f"{batch_num}",
                    'error': f"Error insertando lote: {str(e)}"
                })
        
        print(f"\n🏁 Importación finalizada. Total insertados: {total_insertados}") # LOG FINAL

        return {
            "status": "success",
            "mensaje": f"Importación completada",
            "total_filas_csv": len(df),
            "incendios_insertados": total_insertados,
            "errores": errores if errores else None,
            "timestamp": datetime.now().isoformat()
        }
    
    except pd.errors.EmptyDataError:
        raise HTTPException(status_code=400, detail="El archivo CSV está vacío")
    except pd.errors.ParserError as e:
        raise HTTPException(status_code=400, detail=f"Error al parsear el CSV: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error crítico: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error procesando el archivo: {str(e)}")


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