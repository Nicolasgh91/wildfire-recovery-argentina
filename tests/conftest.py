from typing import Generator

import anyio
import fastapi.testclient as fastapi_testclient
import httpx
import pytest
import starlette.testclient as starlette_testclient
from httpx import ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import deps as api_deps
from app.core.config import settings
from app.db.session import get_db
from app.main import app

# -----------------------------------------------------------------------------
# TestClient compatibility shim (starlette 0.27 + httpx 0.28)
# -----------------------------------------------------------------------------


class CompatTestClient:
    __test__ = False

    def __init__(self, app, base_url: str = "http://testserver", **kwargs):
        self.app = app
        self._transport = ASGITransport(app=app)
        self._client = httpx.AsyncClient(
            transport=self._transport,
            base_url=base_url,
            **kwargs,
        )

    def __enter__(self):
        anyio.run(self.app.router.startup)
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            anyio.run(self._client.aclose)
        finally:
            anyio.run(self.app.router.shutdown)

    def __getattr__(self, name):
        return getattr(self._client, name)

    def request(self, method, url, **kwargs):
        async def _do_request():
            return await self._client.request(method, url, **kwargs)

        return anyio.run(_do_request)

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)

    def put(self, url, **kwargs):
        return self.request("PUT", url, **kwargs)

    def patch(self, url, **kwargs):
        return self.request("PATCH", url, **kwargs)

    def delete(self, url, **kwargs):
        return self.request("DELETE", url, **kwargs)


# Patch TestClient to avoid httpx 0.28 incompatibility.
fastapi_testclient.TestClient = CompatTestClient
starlette_testclient.TestClient = CompatTestClient

# -----------------------------------------------------------------------------
# Database Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture(scope="session")
def db_engine():
    """
    Creates a dedicated DB engine for the test session.
    """
    if not settings.TEST_DATABASE_URL:
        raise RuntimeError("TEST_DATABASE_URL is not set")
    engine = create_engine(settings.TEST_DATABASE_URL, pool_pre_ping=True)

    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """
    Creates a new database session for a test.
    Wraps the test in a transaction and rolls it back after the test completes.
    This ensures test isolation.
    """
    connection = db_engine.connect()
    transaction = connection.begin()

    # Bind the session to the connection so it joins the transaction
    session = sessionmaker(bind=connection)()

    yield session

    # Teardown: Close session, rollback transaction, close connection
    session.close()
    transaction.rollback()
    connection.close()


# -----------------------------------------------------------------------------
# Client Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture(scope="function")
def client(db_session):
    """
    TestClient with overridden get_db dependency to use the isolated db_session.
    """

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[api_deps.get_db] = override_get_db

    # Using 'with' context manager to trigger lifespan events (startup/shutdown)
    with fastapi_testclient.TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def admin_client(client):
    """
    Authenticated client with Admin privileges.
    Uses settings.ADMIN_API_KEY.
    """
    key = (
        settings.ADMIN_API_KEY.get_secret_value()
        if settings.ADMIN_API_KEY
        else "admin-test-key"
    )
    client.headers.update({"X-API-Key": key})
    return client


@pytest.fixture(scope="function")
def user_client(client):
    """
    Authenticated client with Standard User privileges.
    Uses settings.API_KEY.
    """
    key = settings.API_KEY.get_secret_value() if settings.API_KEY else "user-test-key"
    client.headers.update({"X-API-Key": key})
    return client
