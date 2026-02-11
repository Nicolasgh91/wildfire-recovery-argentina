"""
Servicio de integración con MercadoPago Checkout Pro.

Encapsula la comunicación con la API de MercadoPago para creación de preferencias
y consulta de estados de pagos.
"""

import asyncio
import hashlib
import hmac
import logging
import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

import mercadopago
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)


class PreferenceItem(BaseModel):
    """Single item for MercadoPago preference creation."""
    title: str
    quantity: int = 1
    unit_price: Decimal
    currency_id: str = "ARS"
    description: Optional[str] = None


class PreferenceResponse(BaseModel):
    """Response payload for MercadoPago preference creation."""
    preference_id: str
    init_point: str
    sandbox_init_point: Optional[str] = None


class PaymentInfo(BaseModel):
    """Simplified payment info returned by MercadoPago."""
    id: str
    status: str
    status_detail: str
    transaction_amount: Decimal
    currency_id: str
    external_reference: Optional[str]
    date_approved: Optional[datetime]
    payer_email: Optional[str]


class MercadoPagoError(Exception):
    """Raised for MercadoPago integration errors."""
    pass


class MercadoPagoService:
    """Singleton wrapper around MercadoPago SDK operations."""
    _instance: Optional["MercadoPagoService"] = None

    def __new__(cls) -> "MercadoPagoService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        mp_token = settings.MERCADOPAGO_ACCESS_TOKEN or settings.MP_ACCESS_TOKEN
        if not mp_token:
            logger.warning(
                "MercadoPago access token not configured; MercadoPago disabled"
            )
            self._sdk = None
        else:
            self._sdk = mercadopago.SDK(mp_token)
        self._webhook_secret = settings.MP_WEBHOOK_SECRET
        self._initialized = True
        logger.info("MercadoPago service initialized")

    async def create_preference(
        self,
        external_reference: str,
        items: list[PreferenceItem],
        payer_email: Optional[str] = None,
        notification_url: Optional[str] = None,
        back_urls: Optional[dict] = None,
        expires_in_hours: int = 24,
        metadata: Optional[dict] = None,
    ) -> PreferenceResponse:
        if not self._sdk:
            raise MercadoPagoError("MercadoPago access token is required")
        mp_items = [
            {
                "title": item.title,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "currency_id": item.currency_id,
                "description": item.description or item.title,
            }
            for item in items
        ]

        preference_data: dict = {
            "items": mp_items,
            "external_reference": external_reference,
            "expires": True,
            "expiration_date_from": datetime.utcnow().isoformat() + "Z",
            "expiration_date_to": (
                datetime.utcnow() + timedelta(hours=expires_in_hours)
            ).isoformat()
            + "Z",
        }

        if payer_email:
            preference_data["payer"] = {"email": payer_email}
        if notification_url:
            preference_data["notification_url"] = notification_url
        if back_urls:
            preference_data["back_urls"] = back_urls
            preference_data["auto_return"] = "approved"
        if metadata:
            preference_data["metadata"] = metadata

        result = await asyncio.to_thread(self._sdk.preference().create, preference_data)
        if result.get("status") not in (200, 201):
            logger.error("MercadoPago error creating preference: %s", result)
            raise MercadoPagoError(
                result.get("response", {}).get("message", "Unknown MercadoPago error")
            )

        response = result.get("response", {})

        return PreferenceResponse(
            preference_id=str(response.get("id")),
            init_point=response.get("init_point", ""),
            sandbox_init_point=response.get("sandbox_init_point"),
        )

    async def get_payment(self, payment_id: str) -> PaymentInfo:
        if not self._sdk:
            raise MercadoPagoError("MercadoPago access token is required")
        result = await asyncio.to_thread(self._sdk.payment().get, payment_id)
        if result.get("status") != 200:
            logger.error("MercadoPago error getting payment: %s", result)
            raise MercadoPagoError(
                result.get("response", {}).get("message", "Unknown MercadoPago error")
            )

        data = result.get("response", {})

        return PaymentInfo(
            id=str(data.get("id")),
            status=data.get("status"),
            status_detail=data.get("status_detail", ""),
            transaction_amount=Decimal(str(data.get("transaction_amount", 0))),
            currency_id=data.get("currency_id"),
            external_reference=data.get("external_reference"),
            date_approved=data.get("date_approved"),
            payer_email=data.get("payer", {}).get("email"),
        )

    def validate_webhook_signature(
        self,
        x_signature: Optional[str],
        x_request_id: Optional[str],
        data_id: str,
    ) -> bool:
        if not self._webhook_secret:
            logger.warning("Webhook signature validation skipped: no secret configured")
            return True

        if not x_signature or not x_request_id or not data_id:
            logger.warning(
                "Webhook signature validation failed: missing headers/data id"
            )
            return False

        parts: dict[str, str] = {}
        for part in x_signature.split(","):
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            parts[key.strip()] = value.strip()

        ts = parts.get("ts")
        v1 = parts.get("v1")
        if not ts or not v1:
            logger.warning("Invalid x-signature content")
            return False

        if not ts.isdigit():
            logger.warning("Invalid x-signature timestamp")
            return False

        if not re.fullmatch(r"[0-9a-fA-F]{64}", v1):
            logger.warning("Invalid x-signature hash")
            return False

        manifest = f"id:{data_id};request-id:{x_request_id};ts:{ts};"
        expected = hmac.new(
            self._webhook_secret.encode(),
            manifest.encode(),
            hashlib.sha256,
        ).hexdigest()

        is_valid = hmac.compare_digest(expected, v1)
        if not is_valid:
            logger.warning("Webhook signature validation failed")

        return is_valid


mp_service = MercadoPagoService()
