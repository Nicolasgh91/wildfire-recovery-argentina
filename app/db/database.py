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
"""

import os
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

# Variables de entorno para conexión a Supabase
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Construir URL de conexión
# Formato: postgresql://usuario:contraseña@host:puerto/basedatos
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Validar que tenemos credenciales configuradas
if not all([DB_HOST, DB_NAME, DB_USER, DB_PASSWORD]):
    raise ValueError(
        "Credenciales de base de datos no configuradas. "
        "Asegúrate que .env tiene: DB_HOST, DB_NAME, DB_USER, DB_PASSWORD"
    )


# Crear engine de SQLAlchemy
# El engine es la "fábrica" que crea conexiones a la BD.
# Configuramos varios parámetros importantes:

engine = create_engine(
    DATABASE_URL,
    # poolclass=QueuePool proporciona un grupo de conexiones thread-safe.
    # Múltiples requests HTTP pueden acceder al pool simultáneamente sin conflictos.
    # La librería automáticamente devuelve conexiones al pool cuando termina.
    poolclass=QueuePool,
    # pool_size=5 significa mantener 5 conexiones abiertas permanentemente.
    # En desarrollo es suficiente. En producción podría aumentarse.
    pool_size=5,
    # max_overflow=10 significa que si se necesitan más de 5, puede abrir hasta 10
    # más (para picos de demanda). Después de usarlas se descartan.
    max_overflow=10,
    # pool_recycle=3600 recicla conexiones cada hora porque Supabase puede cerrar
    # conexiones inactivas. Esto previene errores "connection closed" después de
    # largos períodos sin actividad.
    pool_recycle=3600,
    # echo=False muestra queries SQL en los logs. Útil para debugging pero baja performance.
    # En producción dejar en False. En desarrollo puedes cambiar a True temporalmente.
    echo=False,
)


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


# Session factory
# Esto crea un "fabricador de sesiones" que genera nuevas sesiones con configuración correcta.
# Una Session es un objeto que representa una "conversación" con la BD.
# Típicamente creas una Session por request HTTP, ejecutas tus queries, y luego la cierras.
SessionLocal = sessionmaker(
    autocommit=False,  # Las queries no se confirman automáticamente
    autoflush=False,  # Los cambios no se flush automáticamente (más control)
    bind=engine,  # Usar el engine que creamos arriba
)


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
    db = SessionLocal()
    try:
        # Yield la sesión para que el endpoint la use
        yield db
    finally:
        # Asegurar que se cierra la sesión aunque haya error
        db.close()


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
    return SessionLocal()


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
        db = SessionLocal()
        # Ejecutar una query simple para verificar conexión
        db.execute("SELECT 1")
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
