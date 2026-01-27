from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Create engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=settings.DB_POOL_PRE_PING,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    echo=settings.DEBUG,  # Log SQL queries in debug mode
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


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
