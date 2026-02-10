from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from app.models.base import Base


class PaymentRequest(Base):
    __tablename__ = "payment_requests"

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    status = Column(String(20), nullable=False, default="pending")
    provider = Column(String(20), nullable=False, default="mercadopago")
    purpose = Column(String(20), nullable=False)
    target_entity_type = Column(String(50))
    target_entity_id = Column(UUID(as_uuid=True))

    amount_usd = Column(Numeric(10, 2), nullable=False)
    amount_ars = Column(Numeric(12, 2))

    external_reference = Column(String(100), unique=True, nullable=False)
    provider_payment_id = Column(String(100))
    provider_preference_id = Column(String(100))
    checkout_url = Column(Text)

    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    expires_at = Column(DateTime(timezone=True))
    approved_at = Column(DateTime(timezone=True))
    webhook_received_at = Column(DateTime(timezone=True))

    retry_count = Column(Integer, nullable=False, default=0)
    metadata_json = Column("metadata", JSONB, nullable=False, default=dict)

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'expired', 'refunded')"
        ),
        CheckConstraint("provider IN ('mercadopago', 'manual', 'promotional')"),
        CheckConstraint("purpose IN ('report', 'credits')"),
    )


class PaymentWebhookLog(Base):
    __tablename__ = "payment_webhook_logs"

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    payment_request_id = Column(UUID(as_uuid=True), ForeignKey("payment_requests.id"))

    received_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    topic = Column(String(50))
    action = Column(String(50))
    mp_payment_id = Column(String(100))

    raw_payload = Column(JSONB, nullable=False)
    processing_result = Column(String(20))
    error_message = Column(Text)
    processing_time_ms = Column(Integer)

    __table_args__ = (
        CheckConstraint(
            "processing_result IN ('success', 'ignored', 'error', 'duplicate')"
        ),
    )


class UserCredits(Base):
    __tablename__ = "user_credits"

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True
    )
    balance = Column(Integer, nullable=False, default=0)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (CheckConstraint("balance >= 0"),)


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    type = Column(String(20), nullable=False)
    payment_request_id = Column(UUID(as_uuid=True), ForeignKey("payment_requests.id"))
    related_entity_type = Column(String(50))
    related_entity_id = Column(UUID(as_uuid=True))
    description = Column(Text)
    metadata_json = Column("metadata", JSONB, nullable=False, default=dict)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "type IN ('purchase', 'grant', 'spend', 'refund', 'expiration', 'adjustment')"
        ),
    )
