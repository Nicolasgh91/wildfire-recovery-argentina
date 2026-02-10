"""
=============================================================================
FORESTGUARD API - EXPLORATIONS ENDPOINTS (UC-09)
=============================================================================

Fire investigation/exploration workflow for non-technical users.

Use Case (UC-09): Investigación de Incendios
    Wizard-friendly endpoints to explore fire event evolution without
    requiring technical GEE knowledge. Users can create investigations,
    add comparison items, get quotes, and generate satellite imagery.

Workflow:
    1. POST /explorations - Create a new investigation
    2. POST /explorations/{id}/items - Add pre/post fire date comparisons
    3. POST /explorations/{id}/quote - Get credit cost estimate
    4. POST /explorations/{id}/generate - Generate imagery (consumes credits)
    5. GET /explorations/{id}/assets - Retrieve generated images

Endpoints:
    POST /explorations - Create investigation
    GET /explorations - List user's investigations
    GET /explorations/{id} - Get investigation details
    PATCH /explorations/{id} - Update investigation title
    POST /explorations/{id}/items - Add comparison item
    DELETE /explorations/{id}/items/{item_id} - Remove item
    POST /explorations/{id}/quote - Get credit cost
    POST /explorations/{id}/generate - Generate imagery
    GET /explorations/{id}/assets - Get generated assets

Authentication:
    All endpoints require JWT authentication.
    Shared assets support token-based access.

Author: ForestGuard Team
Version: 2.0.0
Last Updated: 2026-02-08
=============================================================================
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.api import deps
from app.api.routes.auth import get_current_user, get_current_user_optional
from app.core.rate_limiter import check_rate_limit
from app.models.payment import UserCredits
from app.schemas.exploration import (
    ExplorationAssetsResponse,
    ExplorationCreateRequest,
    ExplorationGenerateResponse,
    ExplorationItemCreateRequest,
    ExplorationItemResponse,
    ExplorationListResponse,
    ExplorationQuoteResponse,
    ExplorationResponse,
    ExplorationUpdateRequest,
)
from app.services.exploration_service import ExplorationService

router = APIRouter()


def get_exploration_service(
    db: Session = Depends(deps.get_db),
) -> ExplorationService:
    return ExplorationService(db)


@router.post(
    "/",
    response_model=ExplorationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(check_rate_limit)],
)
def create_exploration(
    payload: ExplorationCreateRequest,
    service: ExplorationService = Depends(get_exploration_service),
    current_user=Depends(get_current_user),
) -> ExplorationResponse:
    try:
        investigation = service.create_investigation(current_user.id, payload)
    except ValueError as exc:
        if str(exc) == "fire_event_not_found":
            raise HTTPException(
                status_code=404, detail="Evento no encontrado"
            ) from exc
        raise

    return ExplorationResponse(
        id=investigation.id,
        fire_event_id=investigation.fire_event_id,
        title=investigation.title,
        status=investigation.status,
        created_at=investigation.created_at,
        updated_at=investigation.updated_at,
        items=[],
    )


@router.get(
    "/",
    response_model=ExplorationListResponse,
    dependencies=[Depends(check_rate_limit)],
)
def list_explorations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: ExplorationService = Depends(get_exploration_service),
    current_user=Depends(get_current_user),
) -> ExplorationListResponse:
    return service.list_investigations(current_user.id, page, page_size)


@router.get(
    "/{investigation_id}",
    response_model=ExplorationResponse,
    dependencies=[Depends(check_rate_limit)],
)
def get_exploration(
    investigation_id: UUID,
    service: ExplorationService = Depends(get_exploration_service),
    current_user=Depends(get_current_user),
) -> ExplorationResponse:
    investigation = service.get_investigation(
        current_user.id, investigation_id
    )
    if not investigation:
        raise HTTPException(
            status_code=404, detail="Investigacion no encontrada"
        )

    items = service.list_items(investigation.id)
    return ExplorationResponse(
        id=investigation.id,
        fire_event_id=investigation.fire_event_id,
        title=investigation.title,
        status=investigation.status,
        created_at=investigation.created_at,
        updated_at=investigation.updated_at,
        items=[ExplorationItemResponse.model_validate(item) for item in items],
    )


@router.patch(
    "/{investigation_id}",
    response_model=ExplorationResponse,
    dependencies=[Depends(check_rate_limit)],
)
def update_exploration(
    investigation_id: UUID,
    payload: ExplorationUpdateRequest,
    service: ExplorationService = Depends(get_exploration_service),
    current_user=Depends(get_current_user),
) -> ExplorationResponse:
    investigation = service.get_investigation(
        current_user.id, investigation_id
    )
    if not investigation:
        raise HTTPException(
            status_code=404, detail="Investigacion no encontrada"
        )

    updated = service.update_investigation(investigation, payload.title)
    items = service.list_items(updated.id)
    return ExplorationResponse(
        id=updated.id,
        fire_event_id=updated.fire_event_id,
        title=updated.title,
        status=updated.status,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
        items=[ExplorationItemResponse.model_validate(item) for item in items],
    )


@router.post(
    "/{investigation_id}/items",
    response_model=ExplorationItemResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(check_rate_limit)],
)
def add_exploration_item(
    investigation_id: UUID,
    payload: ExplorationItemCreateRequest,
    service: ExplorationService = Depends(get_exploration_service),
    current_user=Depends(get_current_user),
) -> ExplorationItemResponse:
    investigation = service.get_investigation(
        current_user.id, investigation_id
    )
    if not investigation:
        raise HTTPException(
            status_code=404, detail="Investigacion no encontrada"
        )

    try:
        item = service.add_item(investigation, payload)
    except ValueError as exc:
        if str(exc) == "max_items_exceeded":
            raise HTTPException(
                status_code=400, detail="Maximo 12 items por investigacion"
            ) from exc
        raise

    return ExplorationItemResponse.model_validate(item)


@router.delete(
    "/{investigation_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    response_class=Response,
    dependencies=[Depends(check_rate_limit)],
)
def delete_exploration_item(
    investigation_id: UUID,
    item_id: UUID,
    service: ExplorationService = Depends(get_exploration_service),
    current_user=Depends(get_current_user),
) -> None:
    investigation = service.get_investigation(
        current_user.id, investigation_id
    )
    if not investigation:
        raise HTTPException(
            status_code=404, detail="Investigacion no encontrada"
        )

    deleted = service.delete_item(investigation.id, item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{investigation_id}/quote",
    response_model=ExplorationQuoteResponse,
    dependencies=[Depends(check_rate_limit)],
)
def get_exploration_quote(
    investigation_id: UUID,
    service: ExplorationService = Depends(get_exploration_service),
    current_user=Depends(get_current_user),
) -> ExplorationQuoteResponse:
    investigation = service.get_investigation(
        current_user.id, investigation_id
    )
    if not investigation:
        raise HTTPException(
            status_code=404, detail="Investigacion no encontrada"
        )

    try:
        return service.create_quote(investigation)
    except ValueError as exc:
        if str(exc) == "max_items_exceeded":
            raise HTTPException(
                status_code=400, detail="Maximo 12 items por investigacion"
            ) from exc
        raise


@router.post(
    "/{investigation_id}/generate",
    response_model=ExplorationGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(check_rate_limit)],
)
def generate_exploration(
    investigation_id: UUID,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    service: ExplorationService = Depends(get_exploration_service),
    current_user=Depends(get_current_user),
) -> ExplorationGenerateResponse:
    try:
        job, credits_spent, credits_remaining = service.generate_images(
            user_id=current_user.id,
            investigation_id=investigation_id,
            idempotency_key=idempotency_key,
        )
    except ValueError as exc:
        code = str(exc)
        if code == "investigation_not_found":
            raise HTTPException(
                status_code=404, detail="Investigacion no encontrada"
            ) from exc
        if code == "no_items":
            raise HTTPException(
                status_code=400, detail="La investigacion no tiene items"
            ) from exc
        if code == "max_items_exceeded":
            raise HTTPException(
                status_code=400, detail="Maximo 12 items por investigacion"
            ) from exc
        if code == "insufficient_credits":
            items_count = len(service.list_items(investigation_id))
            credits_balance = (
                service.db.query(UserCredits.balance)
                .filter(UserCredits.user_id == current_user.id)
                .scalar()
                or 0
            )
            raise HTTPException(
                status_code=402,
                detail={
                    "message": "Creditos insuficientes",
                    "credits_required": items_count,
                    "credits_balance": credits_balance,
                },
            ) from exc
        raise

    items_count = job.progress_total
    return ExplorationGenerateResponse(
        job_id=job.id,
        status=job.status,
        items_count=items_count,
        credits_spent=credits_spent,
        credits_remaining=credits_remaining,
    )


@router.get(
    "/{investigation_id}/assets",
    response_model=ExplorationAssetsResponse,
    dependencies=[Depends(check_rate_limit)],
)
def list_exploration_assets(
    investigation_id: UUID,
    share_token: Optional[UUID] = Query(
        None, description="Token de acceso compartido"
    ),
    service: ExplorationService = Depends(get_exploration_service),
    current_user=Depends(get_current_user_optional),
) -> ExplorationAssetsResponse:
    if not share_token and not current_user:
        raise HTTPException(status_code=401, detail="Token requerido")

    try:
        return service.list_assets(
            investigation_id=investigation_id,
            user_id=current_user.id if current_user else None,
            share_token=share_token,
        )
    except ValueError as exc:
        code = str(exc)
        if code in ("share_not_found", "share_expired", "share_mismatch"):
            raise HTTPException(
                status_code=404, detail="Acceso compartido invalido"
            ) from exc
        if code == "investigation_not_found":
            raise HTTPException(
                status_code=404, detail="Investigacion no encontrada"
            ) from exc
        if code == "auth_required":
            raise HTTPException(
                status_code=401, detail="Token requerido"
            ) from exc
        if code == "signed_url_failed":
            raise HTTPException(
                status_code=502, detail="Error generando URL firmada"
            ) from exc
        raise
