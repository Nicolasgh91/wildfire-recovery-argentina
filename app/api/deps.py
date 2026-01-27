from typing import Generator
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import SessionLocal


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