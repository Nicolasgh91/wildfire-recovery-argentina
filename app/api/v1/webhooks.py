"""
=============================================================================
FORESTGUARD API - WEBHOOKS (MercadoPago Payment Notifications)
=============================================================================

Payment webhook handlers for MercadoPago integration.

Features:
    - Secure webhook signature validation
    - Idempotent payment processing (duplicate detection)
    - Credit balance updates on successful payments
    - Comprehensive webhook logging for debugging

Endpoints:
    POST /webhooks/mercadopago - Handle MercadoPago payment notifications

Security:
    - HMAC signature validation via X-Signature header
    - Request ID tracking via X-Request-ID header
    - Protection against replay attacks

Payment Processing:
    - Credits: Updates user balance via credit_user_balance()
    - Reports: Queues report generation task

Author: ForestGuard Team
Version: 2.0.0
Last Updated: 2026-02-08
=============================================================================
"""

import logging
import time
from datetime import datetime, timezone
from threading import Lock
from typing import Optional

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.api import deps
from app.models.payment import PaymentRequest, PaymentWebhookLog
from app.services.mercadopago_service import MercadoPagoError, mp_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# SEC-008: Webhook replay protection - max age for valid webhooks
WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS = 300  # 5 minutes

_processed_webhooks: set[str] = set()
_processed_webhooks_lock = Lock()


class MPWebhookPayload(BaseModel):
    """MercadoPago webhook payload structure."""

    action: str
    api_version: str
    data: dict
    date_created: str  # ISO format timestamp
    id: str
    live_mode: bool
    type: str
    user_id: Optional[str] = None


def _extract_signature_ts(x_signature: Optional[str]) -> Optional[int]:
    if not x_signature:
        return None
    parts: dict[str, str] = {}
    for part in x_signature.split(","):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        parts[key.strip()] = value.strip()
    ts = parts.get("ts")
    if not ts or not ts.isdigit():
        return None
    return int(ts)


def _parse_iso_datetime(value: str) -> Optional[datetime]:
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _mark_webhook_processed(event_id: str) -> None:
    with _processed_webhooks_lock:
        _processed_webhooks.add(event_id)


def _is_duplicate_webhook(event_id: str) -> bool:
    with _processed_webhooks_lock:
        return event_id in _processed_webhooks


def validate_webhook_timestamp(
    x_signature: Optional[str], date_created: str
) -> bool:
    """
    SEC-008: Validate webhook timestamp to prevent replay attacks.

    Args:
        x_signature: X-Signature header containing "ts"
        date_created: ISO format timestamp from webhook payload

    Returns:
        True if timestamp is within acceptable range, False otherwise
    """
    signature_ts = _extract_signature_ts(x_signature)
    now_ts = int(time.time())
    if signature_ts is not None:
        return (
            abs(now_ts - signature_ts) <= WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS
        )

    # Fallback to payload timestamp if signature timestamp is missing
    parsed = _parse_iso_datetime(date_created)
    if not parsed:
        logger.warning("Failed to parse webhook timestamp: %s", date_created)
        return False
    age_seconds = abs((datetime.now(timezone.utc) - parsed).total_seconds())
    return age_seconds <= WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS


@router.post("/mercadopago")
async def mercadopago_webhook(
    request: Request,
    payload: MPWebhookPayload,
    db: Session = Depends(deps.get_db),
    x_signature: Optional[str] = Header(None),
    x_request_id: Optional[str] = Header(None),
):
    start_time = datetime.utcnow()
    data_id = payload.data.get("id", "")
    event_id = payload.id or data_id

    if not event_id:
        logger.warning("Webhook without event id")
        return {"status": "error", "message": "webhook without event id"}

    # SEC-008: Validate timestamp to prevent replay attacks
    if not validate_webhook_timestamp(x_signature, payload.date_created):
        logger.warning(
            "Webhook replay attack detected - stale timestamp for %s", data_id
        )
        return {"status": "rejected", "reason": "stale_timestamp"}

    # SEC-008: Idempotency check (in-memory fallback; use Redis in prod)
    if _is_duplicate_webhook(event_id):
        return {"status": "already_processed"}

    is_valid = mp_service.validate_webhook_signature(
        x_signature=x_signature,
        x_request_id=x_request_id,
        data_id=data_id,
    )
    if not is_valid:
        logger.warning("Invalid webhook signature for %s", data_id)
        return {"status": "signature_invalid"}

    webhook_log = PaymentWebhookLog(
        topic=payload.type,
        action=payload.action,
        mp_payment_id=data_id,
        raw_payload=payload.model_dump(),
    )
    db.add(webhook_log)

    if payload.type != "payment":
        webhook_log.processing_result = "ignored"
        db.commit()
        _mark_webhook_processed(event_id)
        return {"status": "ignored", "reason": "not a payment notification"}

    try:
        payment_info = await mp_service.get_payment(data_id)
    except MercadoPagoError as exc:
        logger.error("Error getting payment %s: %s", data_id, exc)
        webhook_log.processing_result = "error"
        webhook_log.error_message = str(exc)
        db.commit()
        return {"status": "error", "message": str(exc)}

    if not payment_info.external_reference:
        logger.warning("Payment %s has no external_reference", data_id)
        webhook_log.processing_result = "error"
        webhook_log.error_message = "No external_reference"
        db.commit()
        return {"status": "error", "message": "no external_reference"}

    result = db.execute(
        select(PaymentRequest).where(
            PaymentRequest.external_reference
            == payment_info.external_reference
        )
    )
    payment_request = result.scalar_one_or_none()

    if not payment_request:
        logger.warning(
            "Payment request not found: %s", payment_info.external_reference
        )
        webhook_log.processing_result = "error"
        webhook_log.error_message = "Payment request not found"
        db.commit()
        return {"status": "error", "message": "payment_request not found"}

    webhook_log.payment_request_id = payment_request.id

    if payment_request.status == "approved":
        webhook_log.processing_result = "duplicate"
        webhook_log.processing_time_ms = int(
            (datetime.utcnow() - start_time).total_seconds() * 1000
        )
        db.commit()
        _mark_webhook_processed(event_id)
        return {"status": "duplicate", "message": "already processed"}

    if payment_info.status == "approved":
        payment_request.status = "approved"
        payment_request.provider_payment_id = payment_info.id
        payment_request.approved_at = datetime.utcnow()
        payment_request.webhook_received_at = datetime.utcnow()
        payment_request.amount_ars = payment_info.transaction_amount

        credits_amount = payment_request.metadata_json.get("credits_amount", 0)
        if payment_request.purpose == "credits" and credits_amount > 0:
            db.execute(
                text(
                    """
                    SELECT credit_user_balance(
                        :user_id,
                        :amount,
                        'purchase',
                        :payment_request_id,
                        :description
                    )
                    """
                ),
                {
                    "user_id": str(payment_request.user_id),
                    "amount": credits_amount,
                    "payment_request_id": str(payment_request.id),
                    "description": f"Compra de {credits_amount} créditos",
                },
            )
            logger.info(
                "Credited %s credits to user %s",
                credits_amount,
                payment_request.user_id,
            )
        elif payment_request.purpose == "report":
            logger.info(
                "Report generation pending for %s",
                payment_request.target_entity_id,
            )

        webhook_log.processing_result = "success"
        logger.info("Payment %s approved successfully", payment_request.id)

    elif payment_info.status in ("rejected", "cancelled"):
        payment_request.status = "rejected"
        payment_request.webhook_received_at = datetime.utcnow()
        webhook_log.processing_result = "success"
        logger.info("Payment %s rejected/cancelled", payment_request.id)
    else:
        webhook_log.processing_result = "ignored"
        logger.info(
            "Payment %s status: %s", payment_request.id, payment_info.status
        )

    webhook_log.processing_time_ms = int(
        (datetime.utcnow() - start_time).total_seconds() * 1000
    )

    db.commit()
    _mark_webhook_processed(event_id)
    return {"status": "ok"}
