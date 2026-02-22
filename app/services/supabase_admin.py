"""
Supabase Auth admin helper operations for account lifecycle.
"""

from __future__ import annotations

import logging
from uuid import UUID

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)


class SupabaseAdminService:
    def __init__(self) -> None:
        self.base_url = (settings.SUPABASE_URL or "").rstrip("/")
        self.anon_key = (
            settings.SUPABASE_ANON_KEY.get_secret_value()
            if settings.SUPABASE_ANON_KEY
            else None
        )
        self.service_key = (
            settings.SUPABASE_SERVICE_KEY.get_secret_value()
            if settings.SUPABASE_SERVICE_KEY
            else None
        )

    def _auth_base(self) -> str:
        if not self.base_url:
            raise RuntimeError("SUPABASE_URL is not configured")
        return f"{self.base_url}/auth/v1"

    def verify_password(self, email: str, password: str) -> bool:
        """
        Verifies current credentials against Supabase password grant.
        Returns False for invalid credentials or transport errors.
        """
        if not email or not password:
            return False
        if not self.anon_key:
            logger.warning("SUPABASE_ANON_KEY missing; cannot verify password server-side")
            return False

        try:
            response = requests.post(
                f"{self._auth_base()}/token?grant_type=password",
                headers={
                    "apikey": self.anon_key,
                    "Content-Type": "application/json",
                },
                json={"email": email, "password": password},
                timeout=10,
            )
            return response.status_code < 400
        except Exception:
            logger.exception("Supabase password verification failed")
            return False

    def revoke_user_sessions(self, user_id: UUID) -> bool:
        """
        Best-effort global sign-out for all active sessions.
        """
        if not self.service_key:
            logger.warning("SUPABASE_SERVICE_KEY missing; skipping global sign-out")
            return False

        headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json",
        }
        # GoTrue admin endpoint for user global sign-out.
        endpoint = f"{self._auth_base()}/admin/users/{user_id}/logout"
        try:
            response = requests.post(endpoint, headers=headers, timeout=10)
            if response.status_code < 400:
                return True
            logger.warning(
                "Supabase global sign-out failed | status=%s | body=%s",
                response.status_code,
                response.text[:300],
            )
            return False
        except Exception:
            logger.exception("Supabase global sign-out request failed")
            return False


supabase_admin_service = SupabaseAdminService()
