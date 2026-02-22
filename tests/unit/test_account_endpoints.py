from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api.v1 import account as account_api


def _fake_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/account/delete",
            "headers": [(b"user-agent", b"pytest")],
            "query_string": b"",
            "client": ("127.0.0.1", 12345),
        }
    )


def _fake_user():
    return SimpleNamespace(
        id=uuid4(),
        email="delete.me@example.com",
        role="user",
        is_deleted=False,
        password_hash="hash",
        google_id=None,
    )


@pytest.mark.asyncio
async def test_delete_challenge_endpoint_returns_neutral_message(monkeypatch):
    async def _fake_issue_delete_challenge(_user):
        return None

    monkeypatch.setattr(account_api, "issue_delete_challenge", _fake_issue_delete_challenge)

    response = await account_api.create_delete_challenge(current_user=_fake_user())
    assert "token temporal" in response.message


@pytest.mark.asyncio
async def test_delete_endpoint_rejects_invalid_confirmation_text():
    payload = account_api.DeleteAccountRequest(
        confirmationText="BORRAR",
        challengeToken="123456",
    )
    with pytest.raises(HTTPException) as exc_info:
        await account_api.delete_account(
            payload=payload,
            request=_fake_request(),
            db=object(),  # type: ignore[arg-type]
            current_user=_fake_user(),  # type: ignore[arg-type]
        )

    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_delete_endpoint_accepts_valid_challenge(monkeypatch):
    monkeypatch.setattr(account_api, "verify_delete_challenge", lambda _user_id, _token: True)
    monkeypatch.setattr(account_api, "verify_password_for_delete", lambda _user, _password: False)
    monkeypatch.setattr(account_api, "soft_delete_account", lambda **_kwargs: None)

    payload = account_api.DeleteAccountRequest(
        confirmationText="ELIMINAR",
        challengeToken="123456",
        reason="test",
    )
    response = await account_api.delete_account(
        payload=payload,
        request=_fake_request(),
        db=object(),  # type: ignore[arg-type]
        current_user=_fake_user(),  # type: ignore[arg-type]
    )

    assert response.message == "Account deleted"


@pytest.mark.asyncio
async def test_delete_endpoint_rejects_when_verification_fails(monkeypatch):
    monkeypatch.setattr(account_api, "verify_delete_challenge", lambda _user_id, _token: False)
    monkeypatch.setattr(account_api, "verify_password_for_delete", lambda _user, _password: False)

    payload = account_api.DeleteAccountRequest(
        confirmationText="ELIMINAR",
        challengeToken="000000",
    )

    with pytest.raises(HTTPException) as exc_info:
        await account_api.delete_account(
            payload=payload,
            request=_fake_request(),
            db=object(),  # type: ignore[arg-type]
            current_user=_fake_user(),  # type: ignore[arg-type]
        )

    assert exc_info.value.status_code == 401
