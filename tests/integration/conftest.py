"""Fixtures for integration tests."""
from __future__ import annotations

import pytest

from app.db.session import SessionLocal


@pytest.fixture
def db_session():
    """
    Provide a real DB session for integration tests.
    Wraps work in a transaction that is rolled back so tests are isolated.
    """
    from sqlalchemy.exc import ResourceClosedError

    db = SessionLocal()
    trans = db.begin()
    try:
        yield db
    finally:
        try:
            trans.rollback()
        except ResourceClosedError:
            pass
        try:
            db.close()
        except Exception:
            pass
