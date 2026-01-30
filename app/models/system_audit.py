
from sqlalchemy import Column, String, DateTime, text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from app.db.base import Base

class AuditEvent(Base):
    """
    Centralized Audit Log for persistent tracking of critical actions.
    Append-only (by convention).
    """
    __tablename__ = "audit_events"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    
    # Who
    principal_id = Column(String(255))      # API Key / User ID
    principal_role = Column(String(50))     # admin, user, public
    
    # What
    action = Column(String(100), nullable=False)
    
    # Where (Resource)
    resource_type = Column(String(100))
    resource_id = Column(UUID(as_uuid=True))
    
    # Context
    details = Column(JSONB)
    ip_address = Column(INET)
    user_agent = Column(String)
    
    # When
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
