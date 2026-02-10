from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class UserInvestigation(Base):
    __tablename__ = "user_investigations"

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    title = Column(Text)
    fire_event_id = Column(UUID(as_uuid=True), ForeignKey("fire_events.id"))
    status = Column(String(20), nullable=False, default="draft")
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    items = relationship(
        "InvestigationItem",
        back_populates="investigation",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'quoted', 'processing', 'ready', 'failed')"
        ),
    )


class InvestigationItem(Base):
    __tablename__ = "investigation_items"

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    investigation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user_investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind = Column(String(10), nullable=False)
    target_date = Column(DateTime(timezone=True), nullable=False)
    sensor = Column(String(50))
    aoi = Column(JSONB)
    geometry_ref = Column(Text)
    visualization_params = Column(JSONB)
    status = Column(String(20), nullable=False, default="pending")
    error = Column(Text)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    investigation = relationship("UserInvestigation", back_populates="items")
    assets = relationship(
        "InvestigationAsset",
        back_populates="item",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("kind IN ('pre', 'post')"),
        CheckConstraint("status IN ('pending', 'queued', 'generated', 'failed')"),
    )


class InvestigationAsset(Base):
    __tablename__ = "investigation_assets"

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    investigation_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("investigation_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    gcs_path = Column(Text, nullable=False)
    signed_url_cache = Column(JSONB)
    mime = Column(Text)
    width = Column(Integer)
    height = Column(Integer)
    sha256 = Column(Text)
    generated_at = Column(DateTime(timezone=True))
    recipe = Column(JSONB)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    item = relationship("InvestigationItem", back_populates="assets")


class InvestigationShare(Base):
    __tablename__ = "investigation_shares"

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    investigation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user_investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    share_token = Column(
        UUID(as_uuid=True), nullable=False, server_default=text("gen_random_uuid()")
    )
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class HdGenerationJob(Base):
    __tablename__ = "hd_generation_jobs"

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    investigation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user_investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    idempotency_key = Column(Text)
    status = Column(String(20), nullable=False, default="queued")
    progress_total = Column(Integer, nullable=False, default=0)
    progress_done = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("status IN ('queued', 'processing', 'ready', 'failed')"),
    )
