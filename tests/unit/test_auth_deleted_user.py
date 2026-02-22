from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request

from app.api import auth_deps


@pytest.mark.asyncio
async def test_get_current_user_rejects_soft_deleted_user(monkeypatch):
    user_id = str(uuid4())

    monkeypatch.setattr(auth_deps, "decode_supabase_token", lambda _token: {"sub": user_id})
    monkeypatch.setattr(
        auth_deps,
        "get_or_create_supabase_user",
        lambda _db, _payload: SimpleNamespace(id=user_id, is_deleted=True),
    )

    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/account/delete",
            "headers": [],
            "query_string": b"",
            "client": ("127.0.0.1", 12345),
        }
    )
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")

    with pytest.raises(HTTPException) as exc_info:
        await auth_deps.get_current_user(
            request=request,
            credentials=credentials,
            db=object(),  # type: ignore[arg-type]
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Cuenta eliminada"
