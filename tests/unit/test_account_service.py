from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services import account_service


@pytest.mark.asyncio
async def test_issue_and_verify_delete_challenge(monkeypatch):
    user = SimpleNamespace(id=uuid4(), email="account.test@example.com")

    async def _fake_send_email(_message):
        return None

    monkeypatch.setattr(account_service, "send_email", _fake_send_email)
    monkeypatch.setattr(account_service.secrets, "randbelow", lambda _n: 123456)

    await account_service.issue_delete_challenge(user)

    assert account_service.verify_delete_challenge(user.id, "123456") is True
    # Token is single-use.
    assert account_service.verify_delete_challenge(user.id, "123456") is False


def test_soft_delete_account_marks_user_and_nulls_reports(monkeypatch):
    user_id = uuid4()
    user = SimpleNamespace(
        id=user_id,
        email="test@example.com",
        role="user",
        is_deleted=False,
        deleted_at=None,
        deletion_reason=None,
        full_name="Test User",
    )

    class DummyDB:
        def __init__(self):
            self.executed = []
            self.audit_events = []
            self.committed = False
            self.refreshed = False

        def execute(self, statement, params):
            self.executed.append((str(statement), params))

        def add(self, value):
            self.audit_events.append(value)

        def commit(self):
            self.committed = True

        def refresh(self, _value):
            self.refreshed = True

    db = DummyDB()
    monkeypatch.setattr(
        account_service.supabase_admin_service, "revoke_user_sessions", lambda _user_id: True
    )

    account_service.soft_delete_account(
        db=db,  # type: ignore[arg-type]
        user=user,  # type: ignore[arg-type]
        deletion_reason="test_case",
        ip_address="127.0.0.1",
        user_agent="pytest",
    )

    assert any("citizen_reports" in stmt for stmt, _params in db.executed)
    assert user.is_deleted is True
    assert user.deleted_at is not None
    assert user.deletion_reason == "test_case"
    assert user.email.startswith("deleted+")
    assert db.committed is True
    assert db.refreshed is True
