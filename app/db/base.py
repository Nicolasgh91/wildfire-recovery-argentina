from sqlalchemy import Column, DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

# 1. Creamos la Clase Base de la que heredarán todos los modelos
Base = declarative_base()

# 2. Definimos Mixins (Atajos para reutilizar código)


class UUIDMixin:
    """Añade una ID tipo UUID generada automáticamente"""

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )


class TimestampMixin:
    """Añade created_at y updated_at automáticos"""

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
