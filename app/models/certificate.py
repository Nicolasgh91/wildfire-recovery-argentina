import hashlib
import json

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base, TimestampMixin, UUIDMixin


class BurnCertificate(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "burn_certificates"

    # Relación con el incendio
    fire_event_id = Column(
        UUID(as_uuid=True), ForeignKey("fire_events.id"), nullable=False
    )

    # Datos del solicitante y Emisión
    issued_to = Column(String, nullable=False)  # Nombre del titular/campo
    requester_email = Column(String, nullable=True)  # Del archivo original
    certificate_number = Column(
        String, unique=True, nullable=False
    )  # Ej: FG-CERT-2026-00001

    # Seguridad
    data_hash = Column(String(64), nullable=False, unique=True)  # SHA256
    snapshot_data = Column(Text, nullable=False)  # JSON con los datos congelados
    verification_url = Column(String)

    # Validez
    issued_at = Column(DateTime(timezone=True), server_default=func.now())
    valid_until = Column(DateTime(timezone=True))  # 90 días de validez
    status = Column(String, default="VALID")  # VALID, REVOKED

    fire_event = relationship("FireEvent")

    def generate_hash(self, payload: dict) -> str:
        """Genera hash SHA256 determinista"""
        content = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()
