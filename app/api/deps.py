from typing import Generator

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.redis_service import redis_client


def get_db() -> Generator:
    """
    Database session dependency.

    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_redis():
    """Redis client dependency for SEO sitemap lock and other API use."""
    return redis_client
