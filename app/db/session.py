from __future__ import annotations

from threading import Lock

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

_engine_lock = Lock()
_engine: Engine | None = None
_session_factory: sessionmaker | None = None


def ensure_database_url_configured(*, context: str = "database bootstrap") -> str:
    """
    Validate DATABASE_URL before creating SQLAlchemy engine/session.

    Keeping this check explicit gives worker startup errors that are actionable
    instead of cryptic stack traces from SQLAlchemy internals.
    """
    raw = settings.DATABASE_URL
    db_url = raw.strip() if isinstance(raw, str) else None
    if db_url:
        return db_url

    raise RuntimeError(
        "DATABASE_URL is required for runtime DB access "
        f"({context}). Configure DATABASE_URL in environment or .env "
        "before starting API/Celery workers."
    )


def get_engine() -> Engine:
    global _engine
    if _engine is not None:
        return _engine

    with _engine_lock:
        if _engine is None:
            _engine = create_engine(
                ensure_database_url_configured(context="SQLAlchemy engine init"),
                pool_pre_ping=settings.DB_POOL_PRE_PING,
                pool_size=settings.DB_POOL_SIZE,
                max_overflow=settings.DB_MAX_OVERFLOW,
                echo=settings.DEBUG,  # Log SQL queries in debug mode
            )
    return _engine


def _get_session_factory() -> sessionmaker:
    global _session_factory
    if _session_factory is not None:
        return _session_factory

    with _engine_lock:
        if _session_factory is None:
            _session_factory = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=get_engine(),
            )
    return _session_factory


def SessionLocal() -> Session:
    return _get_session_factory()()


def get_db():
    """
    Dependency for FastAPI endpoints.

    Usage:
        @app.get("/fires")
        def get_fires(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
