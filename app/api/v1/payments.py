"""
=============================================================================
FORESTGUARD API - PAYMENTS ENDPOINTS (MercadoPago Checkout Pro)
=============================================================================

Payment processing for ForestGuard services using MercadoPago integration.

Features:
    - Credit purchases with package discounts
    - Report generation payments
    - Real-time USD/ARS exchange rate conversion (BNA rates)
    - Paginated transaction history

Endpoints:
    POST /payments/checkout - Create payment session
    GET /payments/pricing - Get current pricing and packages
    GET /payments/{id}/status - Check payment status
    GET /payments/credits/balance - Get user's credit balance
    GET /payments/credits/transactions - Transaction history (SEC-001: max 100/page)

Security:
    - All endpoints require JWT authentication
    - Rate limiting enabled on checkout creation
    - Transaction isolation for concurrent purchases

Credit Packages:
    - 5 credits: $2.50 USD
    - 12 credits: $5.00 USD
    - 25 credits: $10.00 USD
    - Individual: $0.50 USD each

Author: ForestGuard Team
Version: 2.0.0
Last Updated: 2026-02-08
=============================================================================
"""

from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.api import deps
from app.api.auth_deps import get_current_user
from app.core.config import settings
from app.core.rate_limiter import check_rate_limit
from app.models.payment import CreditTransaction, PaymentRequest
from app.services.exchange_rate_service import get_bna_usd_ars_rate
from app.services.mercadopago_service import (
    MercadoPagoError,
    PreferenceItem,
    mp_service,
)

router = APIRouter()


class CreateCheckoutRequest(BaseModel):
    purpose: str = Field(..., pattern="^(report|credits)$")
    target_entity_type: Optional[str] = None
    target_entity_id: Optional[UUID] = None
    credits_amount: Optional[int] = Field(None, ge=1, le=100)
    metadata: Optional[dict] = None
    client_platform: Optional[str] = Field(None, pattern="^(web|android)$")


class CreateCheckoutResponse(BaseModel):
    payment_request_id: UUID
    checkout_url: str
    external_reference: str
    amount_usd: Decimal
    amount_ars: Decimal
    exchange_rate: Decimal
    expires_at: datetime


class PaymentStatusResponse(BaseModel):
    id: UUID
    status: str
    purpose: str
    amount_usd: Decimal
    amount_ars: Optional[Decimal] = None
    created_at: datetime
    approved_at: Optional[datetime] = None


CREDIT_PRICE_USD = Decimal("0.50")

CREDIT_PACKAGES = {
    5: Decimal("2.50"),
    12: Decimal("5.00"),
    25: Decimal("10.00"),
}


def _append_payment_request_id(url: str, payment_request_id: UUID) -> str:
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}payment_request_id={payment_request_id}"


def _build_back_urls(payment_request_id: UUID, platform: str) -> dict:
    if platform == "android":
        success = settings.PAYMENT_SUCCESS_URL_ANDROID or settings.PAYMENT_SUCCESS_URL
        failure = settings.PAYMENT_FAILURE_URL_ANDROID or settings.PAYMENT_FAILURE_URL
        pending = settings.PAYMENT_PENDING_URL_ANDROID or settings.PAYMENT_PENDING_URL
    else:
        success = settings.PAYMENT_SUCCESS_URL
        failure = settings.PAYMENT_FAILURE_URL
        pending = settings.PAYMENT_PENDING_URL

    return {
        "success": _append_payment_request_id(success, payment_request_id),
        "failure": _append_payment_request_id(failure, payment_request_id),
        "pending": _append_payment_request_id(pending, payment_request_id),
    }


def calculate_price(purpose: str, credits_amount: Optional[int]) -> Decimal:
    if purpose == "credits":
        if credits_amount in CREDIT_PACKAGES:
            return CREDIT_PACKAGES[credits_amount]
        return CREDIT_PRICE_USD * Decimal(credits_amount or 0)
    return Decimal("6.00")


def convert_usd_to_ars(amount_usd: Decimal, rate: Decimal) -> Decimal:
    return (amount_usd * rate).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


@router.post(
    "/checkout",
    response_model=CreateCheckoutResponse,
    dependencies=[Depends(check_rate_limit)],
)
async def create_checkout(
    request: CreateCheckoutRequest,
    db: Session = Depends(deps.get_db),
    current_user=Depends(get_current_user),
):
    platform = request.client_platform or "web"
    if request.purpose == "credits" and not request.credits_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="credits_amount is required when purpose is 'credits'",
        )

    if request.purpose == "report" and not request.target_entity_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="target_entity_id is required when purpose is 'report'",
        )

    amount_usd = calculate_price(request.purpose, request.credits_amount)
    rate_info = await get_bna_usd_ars_rate()
    amount_ars = convert_usd_to_ars(amount_usd, rate_info.rate)
    external_reference = f"fg_{uuid4().hex[:16]}"
    expires_at = datetime.utcnow() + timedelta(hours=24)

    payment_request = PaymentRequest(
        user_id=current_user.id,
        status="pending",
        provider="mercadopago",
        purpose=request.purpose,
        target_entity_type=request.target_entity_type,
        target_entity_id=request.target_entity_id,
        amount_usd=amount_usd,
        amount_ars=amount_ars,
        external_reference=external_reference,
        expires_at=expires_at,
        metadata_json={
            "credits_amount": request.credits_amount,
            "usd_ars_rate": str(rate_info.rate),
            **(request.metadata or {}),
        },
    )

    db.add(payment_request)
    db.flush()

    back_urls = _build_back_urls(payment_request.id, platform)

    if settings.MP_MOCK_MODE:
        payment_request.provider_preference_id = (
            f"mock_pref_{uuid4().hex[:12]}"
        )
        payment_request.checkout_url = back_urls["success"]

        if settings.MP_MOCK_APPROVE:
            payment_request.status = "approved"
            payment_request.approved_at = datetime.utcnow()
            payment_request.webhook_received_at = datetime.utcnow()
            payment_request.provider_payment_id = (
                f"mock_pay_{uuid4().hex[:12]}"
            )

            credits_amount = payment_request.metadata_json.get(
                "credits_amount", 0
            )
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
                        "description": f"Compra de {credits_amount} créditos (mock)",
                    },
                )

        db.commit()
        return CreateCheckoutResponse(
            payment_request_id=payment_request.id,
            checkout_url=payment_request.checkout_url,
            external_reference=external_reference,
            amount_usd=amount_usd,
            amount_ars=amount_ars,
            exchange_rate=rate_info.rate,
            expires_at=expires_at,
        )

    if request.purpose == "credits":
        title = f"ForestGuard - {request.credits_amount} créditos"
        description = (
            f"Paquete de {request.credits_amount} créditos para reportes HD"
        )
    else:
        title = "ForestGuard - Reporte HD"
        description = "Generación de reporte con imágenes satelitales HD"

    items = [
        PreferenceItem(
            title=title,
            description=description,
            unit_price=amount_ars,
            quantity=1,
            currency_id="ARS",
        )
    ]

    try:
        preference = await mp_service.create_preference(
            external_reference=external_reference,
            items=items,
            payer_email=current_user.email,
            notification_url=settings.MP_NOTIFICATION_URL,
            back_urls=back_urls,
            expires_in_hours=24,
            metadata={
                "user_id": str(current_user.id),
                "purpose": request.purpose,
                "payment_request_id": str(payment_request.id),
            },
        )
    except MercadoPagoError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error creating payment preference: {str(exc)}",
        ) from exc

    payment_request.provider_preference_id = preference.preference_id
    payment_request.checkout_url = preference.init_point

    db.commit()

    return CreateCheckoutResponse(
        payment_request_id=payment_request.id,
        checkout_url=preference.init_point,
        external_reference=external_reference,
        amount_usd=amount_usd,
        amount_ars=amount_ars,
        exchange_rate=rate_info.rate,
        expires_at=expires_at,
    )


@router.get(
    "/pricing",
    dependencies=[Depends(check_rate_limit), Depends(get_current_user)],
)
async def get_pricing():
    rate_info = await get_bna_usd_ars_rate()
    credit_packages = []
    for credits, price_usd in sorted(CREDIT_PACKAGES.items()):
        credit_packages.append(
            {
                "credits": credits,
                "price_usd": price_usd,
                "price_ars": convert_usd_to_ars(price_usd, rate_info.rate),
            }
        )

    report_price_usd = calculate_price("report", None)

    return {
        "currency": "ARS",
        "exchange_rate": rate_info.rate,
        "fetched_at": rate_info.fetched_at.isoformat(),
        "source": rate_info.source_url,
        "credit_packages": credit_packages,
        "report_price_usd": report_price_usd,
        "report_price_ars": convert_usd_to_ars(
            report_price_usd, rate_info.rate
        ),
    }


@router.get("/{payment_request_id}", response_model=PaymentStatusResponse)
async def get_payment_status(
    payment_request_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user=Depends(get_current_user),
):
    result = db.execute(
        select(PaymentRequest).where(
            PaymentRequest.id == payment_request_id,
            PaymentRequest.user_id == current_user.id,
        )
    )
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment request not found",
        )

    return PaymentStatusResponse(
        id=payment.id,
        status=payment.status,
        purpose=payment.purpose,
        amount_usd=payment.amount_usd,
        amount_ars=payment.amount_ars,
        created_at=payment.created_at,
        approved_at=payment.approved_at,
    )


@router.get("/credits/balance", dependencies=[Depends(check_rate_limit)])
async def get_credit_balance(
    db: Session = Depends(deps.get_db),
    current_user=Depends(get_current_user),
):
    result = db.execute(
        text("SELECT * FROM get_or_create_user_credits(:user_id)"),
        {"user_id": str(current_user.id)},
    )
    row = result.fetchone()

    last_updated = row.updated_at if row else datetime.utcnow()
    return {
        "balance": row.balance if row else 0,
        "last_updated": last_updated.isoformat(),
    }


@router.get("/credits/transactions", dependencies=[Depends(check_rate_limit)])
async def get_credit_transactions(
    page: int = Query(default=1, ge=1, description="Número de página"),
    page_size: int = Query(
        default=20, ge=1, le=100, description="Items por página (máximo 100)"
    ),
    db: Session = Depends(deps.get_db),
    current_user=Depends(get_current_user),
):
    offset = (page - 1) * page_size

    count_result = db.execute(
        select(func.count())
        .select_from(CreditTransaction)
        .where(CreditTransaction.user_id == current_user.id)
    )
    total = count_result.scalar() or 0

    result = db.execute(
        select(CreditTransaction)
        .where(CreditTransaction.user_id == current_user.id)
        .order_by(CreditTransaction.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    transactions = result.scalars().all()

    return {
        "transactions": [
            {
                "id": str(t.id),
                "amount": t.amount,
                "type": t.type,
                "description": t.description,
                "created_at": t.created_at.isoformat(),
            }
            for t in transactions
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
