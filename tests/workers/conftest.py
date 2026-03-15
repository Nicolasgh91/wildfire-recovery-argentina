"""
Fixtures for workers tests.

- db_session: real SQLAlchemy session (uses app.db.session.SessionLocal).
  When used, SessionLocal in workers.tasks.seo is patched so export_ssg_artifacts
  uses this session (same DB, so seeded data is visible to the task).
- mocker: patch helper (like pytest-mock); patches are reverted after the test.
- mock_oci: in-memory store simulating OCI uploads (put_object, get_uploaded, uploaded_keys).
- settings_override: object to override app.core.config.settings attributes in tests.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.db.session import SessionLocal


class _Mocker:
    """Minimal mocker fixture: patch() starts a patch and returns the mock; all patches are stopped in teardown."""

    def __init__(self):
        self._patchers = []

    def patch(self, target, **kwargs):
        p = patch(target, **kwargs)
        self._patchers.append(p)
        return p.start()

    def stopall(self):
        for p in reversed(self._patchers):
            try:
                p.stop()
            except Exception:
                pass
        self._patchers.clear()


@pytest.fixture
def mocker():
    m = _Mocker()
    yield m
    m.stopall()


@pytest.fixture
def db_session():
    """
    Provide a real DB session for worker tests. Wraps work in a transaction that is
    rolled back so tests are isolated and do not leave data or hit duplicate keys.
    Task code that calls SessionLocal() will get this session when patched.
    The task may call db.close(); teardown tolerates an already-closed transaction.
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


@pytest.fixture(autouse=True)
def patch_seo_session_local(request):
    """
    When a test requests db_session, patch workers.tasks.seo.SessionLocal so that
    export_ssg_artifacts() uses the same session (seeded data is visible).
    """
    if "db_session" not in request.fixturenames:
        yield
        return
    db = request.getfixturevalue("db_session")
    with patch("workers.tasks.seo.SessionLocal", lambda: db):
        yield


class MockOCIStore:
    """In-memory store for OCI uploads: put_object(key, data), get_uploaded(key), uploaded_keys()."""

    def __init__(self):
        self._uploads: dict[str, bytes] = {}

    def put_object(self, key: str, data: bytes, **kwargs):
        self._uploads[key] = data

    def get_uploaded(self, key: str) -> bytes:
        return self._uploads[key]

    def uploaded_keys(self):
        return list(self._uploads.keys())


@pytest.fixture
def mock_oci():
    return MockOCIStore()


@pytest.fixture
def settings_override(mocker):
    """Patch app.core.config.settings so tests can override SITE_BASE_URL etc."""
    return mocker.patch("app.core.config.settings")
