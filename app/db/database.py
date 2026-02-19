"""
Database Configuration para ForestGuard
Maneja la conexión a Supabase PostgreSQL con SQLAlchemy

La razón por la que esto está separado en su propio archivo es que necesitamos
crear la conexión una sola vez y reutilizarla en toda la aplicación. Esto se llama
"session factory pattern" y es fundamental para performance y estabilidad.

Cuando usamos connection pooling (que está habilitado por defecto en SQLAlchemy),
la librería mantiene un grupo de conexiones abiertas a la BD. Cuando necesitamos
consultar, tomamos una conexión del pool en lugar de abrir una nueva cada vez.
Esto es mucho más rápido, especialmente cuando hay muchas consultas simultáneas.

NOTA: La URL de conexión se ensambla en app.core.config (Settings.assemble_db_connection)
para garantizar una única fuente de verdad y el correcto URL-encoding del password.
Este módulo delega al engine/session de app.db.session para evitar duplicación.
"""

from typing import Generator

from sqlalchemy import event, text
from sqlalchemy.orm import Session

from app.db.session import SessionLocal as _SessionLocal
from app.db.session import get_db as _get_db
from app.db.session import get_engine


# Re-export engine y SessionLocal para compatibilidad con importaciones existentes
engine = get_engine()

SessionLocal = _SessionLocal


# Event listener para habilitar PostGIS en cada conexión
# PostGIS es la extensión geoespacial de PostgreSQL. Necesita estar activada
# para que nuestros campos Geometry funcionen correctamente.
# Este listener corre cada vez que se abre una nueva conexión.
@event.listens_for(engine, "connect")
def setup_postgis(dbapi_conn, connection_record):
    """
    Ejecuta comandos SQL cuando se abre una nueva conexión.
    Esto asegura que PostGIS está disponible en la BD.
    """
    # Ejecutar comando para habilitar la extensión PostGIS
    with dbapi_conn.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        dbapi_conn.commit()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency injection para FastAPI.

    Esta función se usa con el sistema de "dependencias" de FastAPI.
    Cuando un endpoint necesita acceso a la BD, FastAPI inyecta automáticamente
    una Session creada por esta función. Después que el endpoint termina,
    FastAPI automáticamente cierra la sesión.

    Esto se usa en FastAPI de esta forma:

        @app.get("/fire-events")
        def list_events(db: Session = Depends(get_db)):
            return db.query(FireEvent).all()

    El parámetro "db" es inyectado automáticamente por FastAPI.
    """
    yield from _get_db()


def get_db_sync() -> Session:
    """
    Alternativa síncrona para obtener una sesión.

    Usar esto cuando necesites acceso a BD fuera de un request HTTP,
    como en Celery workers o scripts de utilidad.

    Ejemplo en un worker Celery:

        @celery_app.task
        def process_fire(fire_id):
            db = get_db_sync()
            try:
                fire = db.query(FireEvent).filter(FireEvent.id == fire_id).first()
                # ... procesar fire ...
                db.commit()
            finally:
                db.close()

    IMPORTANTE: Debes llamar a close() cuando termines para devolver
    la conexión al pool.
    """
    return _SessionLocal()


# Health check para validar que la BD está disponible
def test_connection():
    """
    Función para validar que podemos conectar a Supabase.

    Esto se puede llamar en startup de la aplicación para verificar
    que todo está configurado correctamente antes de servir requests.

    Ejemplo en FastAPI:

        @app.on_event("startup")
        async def startup_event():
            test_connection()
            logger.info("Database connection verified")

    Si hay error de conexión, levantará excepción que FastAPI cachará
    en el health check.
    """
    try:
        db = _SessionLocal()
        # Ejecutar una query simple para verificar conexión
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception as e:
        print(f"Error de conexión a BD: {e}")
        return False


# Para migraciones con Alembic
# Si usas Alembic para gestionar cambios de schema, necesitarás esta referencia.
# En alembic/env.py incluirías algo como:
#
#   from database import engine, Base
#   target_metadata = Base.metadata
#
# Esto permite a Alembic conocer el schema esperado basado en tus modelos.
