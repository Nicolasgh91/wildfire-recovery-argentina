"""
=============================================================================
FORESTGUARD - EXPLORATION SERVICE (UC-15, UC-16)
=============================================================================

Service for user investigations and HD satellite imagery generation.

Features:
    - Create and manage user investigations linked to fire events
    - Timeline items for before/during/after fire imagery
    - HD image generation via GEE with credit-based payment
    - Asset management with signed URL caching
    - Investigation sharing via time-limited tokens

Use Cases:
    UC-15: Create Exploration - Start investigation for a fire event
    UC-16: Generate HD Images - Request high-resolution satellite imagery

Payment Flow:
    1. User creates investigation → draft status
    2. Adds timeline items (max 12 per investigation)
    3. Creates quote → gets price in ARS/credits
    4. Confirms generation → credits deducted, job queued
    5. Worker generates images → status → ready
    6. User downloads via signed URLs

Dependencies:
    - app.models.exploration: UserInvestigation, InvestigationItem, etc.
    - app.models.payment: UserCredits, CreditTransaction
    - app.services.storage_service: For signed URL generation

Author: ForestGuard Team
Version: 2.0.0
Last Updated: 2026-02-08
=============================================================================
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.exploration import (
    HdGenerationJob,
    InvestigationAsset,
    InvestigationItem,
    InvestigationShare,
    UserInvestigation,
)
from app.models.fire import FireEvent
from app.models.payment import CreditTransaction, UserCredits
from app.schemas.exploration import (
    ExplorationAssetResponse,
    ExplorationAssetsResponse,
    ExplorationCreateRequest,
    ExplorationItemCreateRequest,
    ExplorationListItem,
    ExplorationListResponse,
    ExplorationQuoteResponse,
    PaginationMeta,
)
from app.services.storage_service import BUCKETS, StorageService


class ExplorationService:
    """Service for satellite exploration workflows and pricing."""
    def __init__(self, db: Session):
        self.db = db

    def _log_metric(self, name: str, value: float, **labels: object) -> None:
        payload = {"metric": name, "value": value, "labels": labels}
        logging.getLogger(__name__).info(
            "metric=%s", json.dumps(payload, ensure_ascii=True)
        )

    @staticmethod
    def _normalize_datetime(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _get_system_param_value(self, key: str) -> Optional[int]:
        try:
            row = (
                self.db.execute(
                    text(
                        "SELECT param_value FROM system_parameters WHERE param_key = :key"
                    ),
                    {"key": key},
                )
                .mappings()
                .first()
            )
        except SQLAlchemyError:
            return None

        if not row:
            return None

        value = row.get("param_value")
        if isinstance(value, dict) and "value" in value:
            value = value["value"]
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _resolve_unit_price_ars(self, fallback: int = 500) -> int:
        value = self._get_system_param_value("exploration_image_cost_ars")
        if value is not None:
            return value
        value = self._get_system_param_value("report_image_cost_ars")
        if value is not None:
            return value
        return fallback

    def create_investigation(
        self, user_id: UUID, payload: ExplorationCreateRequest
    ) -> UserInvestigation:
        fire_exists = (
            self.db.query(FireEvent.id)
            .filter(FireEvent.id == payload.fire_event_id)
            .first()
        )
        if not fire_exists:
            raise ValueError("fire_event_not_found")

        investigation = UserInvestigation(
            user_id=user_id,
            fire_event_id=payload.fire_event_id,
            title=payload.title,
            status="draft",
        )
        self.db.add(investigation)
        self.db.commit()
        self.db.refresh(investigation)
        return investigation

    def list_investigations(
        self, user_id: UUID, page: int, page_size: int
    ) -> ExplorationListResponse:
        if page < 1:
            page = 1
        page_size = max(1, min(page_size, 100))

        count_query = (
            self.db.query(func.count(UserInvestigation.id))
            .filter(UserInvestigation.user_id == user_id)
            .scalar()
            or 0
        )

        items_count_subq = (
            self.db.query(
                InvestigationItem.investigation_id,
                func.count(InvestigationItem.id).label("items_count"),
            )
            .group_by(InvestigationItem.investigation_id)
            .subquery()
        )

        rows = (
            self.db.query(UserInvestigation, items_count_subq.c.items_count)
            .outerjoin(
                items_count_subq,
                items_count_subq.c.investigation_id == UserInvestigation.id,
            )
            .filter(UserInvestigation.user_id == user_id)
            .order_by(UserInvestigation.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        investigations: List[ExplorationListItem] = []
        for investigation, items_count in rows:
            investigations.append(
                ExplorationListItem(
                    id=investigation.id,
                    fire_event_id=investigation.fire_event_id,
                    title=investigation.title,
                    status=investigation.status,
                    created_at=investigation.created_at,
                    updated_at=investigation.updated_at,
                    items_count=items_count or 0,
                )
            )

        return ExplorationListResponse(
            investigations=investigations,
            pagination=PaginationMeta.create(count_query, page, page_size),
        )

    def get_investigation(
        self, user_id: UUID, investigation_id: UUID
    ) -> Optional[UserInvestigation]:
        return (
            self.db.query(UserInvestigation)
            .filter(
                UserInvestigation.id == investigation_id,
                UserInvestigation.user_id == user_id,
            )
            .first()
        )

    def update_investigation(
        self, investigation: UserInvestigation, title: Optional[str]
    ) -> UserInvestigation:
        if title is not None:
            investigation.title = title
        investigation.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(investigation)
        return investigation

    def list_items(self, investigation_id: UUID) -> List[InvestigationItem]:
        return (
            self.db.query(InvestigationItem)
            .filter(InvestigationItem.investigation_id == investigation_id)
            .order_by(InvestigationItem.target_date.asc())
            .all()
        )

    def add_item(
        self,
        investigation: UserInvestigation,
        payload: ExplorationItemCreateRequest,
    ) -> InvestigationItem:
        existing_count = (
            self.db.query(func.count(InvestigationItem.id))
            .filter(InvestigationItem.investigation_id == investigation.id)
            .scalar()
            or 0
        )
        if existing_count >= 12:
            raise ValueError("max_items_exceeded")

        target_date = self._normalize_datetime(payload.target_date)

        item = InvestigationItem(
            investigation_id=investigation.id,
            kind=payload.kind.value,
            target_date=target_date,
            sensor=payload.sensor,
            aoi=payload.aoi,
            geometry_ref=payload.geometry_ref,
            visualization_params=payload.visualization_params,
            status="pending",
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete_item(
        self,
        investigation_id: UUID,
        item_id: UUID,
    ) -> bool:
        item = (
            self.db.query(InvestigationItem)
            .filter(
                InvestigationItem.id == item_id,
                InvestigationItem.investigation_id == investigation_id,
            )
            .first()
        )
        if not item:
            return False
        self.db.delete(item)
        self.db.commit()
        return True

    def create_quote(
        self,
        investigation: UserInvestigation,
    ) -> ExplorationQuoteResponse:
        items_count = (
            self.db.query(func.count(InvestigationItem.id))
            .filter(InvestigationItem.investigation_id == investigation.id)
            .scalar()
            or 0
        )

        if items_count > 12:
            raise ValueError("max_items_exceeded")

        unit_price = self._resolve_unit_price_ars()
        total_price = int(unit_price * items_count)

        suggestions: List[str] = []
        if items_count > 6:
            suggestions.append("Con 6 imagenes ya podes ver cambios trimestrales.")

        if investigation.status == "draft":
            investigation.status = "quoted"
            investigation.updated_at = datetime.now(timezone.utc)
            self.db.commit()

        return ExplorationQuoteResponse(
            items_count=items_count,
            unit_price_ars=unit_price,
            total_price_ars=total_price,
            credits_required=items_count,
            suggestions=suggestions,
        )

    def generate_images(
        self,
        user_id: UUID,
        investigation_id: UUID,
        idempotency_key: str,
    ) -> Tuple[HdGenerationJob, int, int]:
        if not idempotency_key:
            raise ValueError("idempotency_required")

        with self.db.begin():
            investigation = (
                self.db.query(UserInvestigation)
                .filter(
                    UserInvestigation.id == investigation_id,
                    UserInvestigation.user_id == user_id,
                )
                .with_for_update()
                .first()
            )
            if not investigation:
                raise ValueError("investigation_not_found")

            existing_job = (
                self.db.query(HdGenerationJob)
                .filter(
                    HdGenerationJob.investigation_id == investigation.id,
                    HdGenerationJob.idempotency_key == idempotency_key,
                )
                .first()
            )
            if existing_job:
                credits_balance = (
                    self.db.query(UserCredits.balance)
                    .filter(UserCredits.user_id == user_id)
                    .scalar()
                    or 0
                )
                return existing_job, 0, credits_balance

            latest_job = (
                self.db.query(HdGenerationJob)
                .filter(HdGenerationJob.investigation_id == investigation.id)
                .order_by(HdGenerationJob.created_at.desc())
                .first()
            )
            if investigation.status in ("processing", "ready") and latest_job:
                credits_balance = (
                    self.db.query(UserCredits.balance)
                    .filter(UserCredits.user_id == user_id)
                    .scalar()
                    or 0
                )
                return latest_job, 0, credits_balance

            items = (
                self.db.query(InvestigationItem)
                .filter(InvestigationItem.investigation_id == investigation.id)
                .order_by(InvestigationItem.target_date.asc())
                .all()
            )
            items_count = len(items)

            if items_count == 0:
                raise ValueError("no_items")
            if items_count > 12:
                raise ValueError("max_items_exceeded")

            credits_required = items_count

            credits = (
                self.db.query(UserCredits)
                .filter(UserCredits.user_id == user_id)
                .with_for_update()
                .first()
            )
            if not credits:
                credits = UserCredits(user_id=user_id, balance=0)
                self.db.add(credits)
                self.db.flush()

            if credits.balance < credits_required:
                raise ValueError("insufficient_credits")

            credits.balance -= credits_required

            self._log_metric(
                "credits_spent_total",
                credits_required,
                user_id=str(user_id),
                investigation_id=str(investigation.id),
            )

            spend_tx = CreditTransaction(
                user_id=user_id,
                amount=-credits_required,
                type="spend",
                related_entity_type="exploration",
                related_entity_id=investigation.id,
                description=f"Generacion de {credits_required} imagenes HD",
                metadata_json={"idempotency_key": idempotency_key},
            )
            self.db.add(spend_tx)

            job = HdGenerationJob(
                investigation_id=investigation.id,
                status="queued",
                progress_total=items_count,
                progress_done=0,
                idempotency_key=idempotency_key,
            )
            self.db.add(job)

            now = datetime.now(timezone.utc)
            investigation.status = "processing"
            investigation.updated_at = now

            for item in items:
                item.status = "queued"
                item.updated_at = now

            credits_remaining = credits.balance

        return job, credits_required, credits_remaining

    def list_assets(
        self,
        *,
        investigation_id: UUID,
        user_id: Optional[UUID],
        share_token: Optional[UUID],
        expiry_seconds: int = 1800,
    ) -> ExplorationAssetsResponse:
        investigation = None
        if share_token:
            share = (
                self.db.query(InvestigationShare)
                .filter(
                    InvestigationShare.share_token == share_token,
                    InvestigationShare.is_active.is_(True),
                )
                .first()
            )
            if not share:
                raise ValueError("share_not_found")
            if share.expires_at:
                exp = share.expires_at
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if exp < datetime.now(timezone.utc):
                    raise ValueError("share_expired")
            if share.investigation_id != investigation_id:
                raise ValueError("share_mismatch")
            investigation = (
                self.db.query(UserInvestigation)
                .filter(UserInvestigation.id == share.investigation_id)
                .first()
            )
        elif user_id:
            investigation = (
                self.db.query(UserInvestigation)
                .filter(
                    UserInvestigation.id == investigation_id,
                    UserInvestigation.user_id == user_id,
                )
                .first()
            )
        else:
            raise ValueError("auth_required")

        if not investigation:
            raise ValueError("investigation_not_found")

        rows = (
            self.db.query(InvestigationAsset, InvestigationItem)
            .join(
                InvestigationItem,
                InvestigationItem.id == InvestigationAsset.investigation_item_id,
            )
            .filter(InvestigationItem.investigation_id == investigation_id)
            .order_by(InvestigationItem.target_date.asc())
            .all()
        )

        storage = StorageService()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=expiry_seconds)
        cache_updated = False

        assets: List[ExplorationAssetResponse] = []
        for asset, item in rows:
            signed_url = None
            cache = asset.signed_url_cache
            if isinstance(cache, dict):
                cached_url = cache.get("url")
                cached_exp = cache.get("expires_at")
                if cached_url and cached_exp:
                    try:
                        cached_exp_dt = datetime.fromisoformat(cached_exp)
                        if cached_exp_dt.tzinfo is None:
                            cached_exp_dt = cached_exp_dt.replace(tzinfo=timezone.utc)
                        if cached_exp_dt > now:
                            signed_url = cached_url
                    except ValueError:
                        signed_url = None

            if not signed_url:
                signed_url = storage.get_signed_url(
                    key=asset.gcs_path,
                    bucket=BUCKETS["images"],
                    expiry_seconds=expiry_seconds,
                )
                if not signed_url:
                    raise ValueError("signed_url_failed")
                asset.signed_url_cache = {
                    "url": signed_url,
                    "expires_at": expires_at.isoformat(),
                }
                cache_updated = True

            assets.append(
                ExplorationAssetResponse(
                    id=asset.id,
                    item_id=item.id,
                    signed_url=signed_url,
                    mime=asset.mime,
                    width=asset.width,
                    height=asset.height,
                    sha256=asset.sha256,
                    generated_at=asset.generated_at,
                    target_date=item.target_date,
                    kind=item.kind,
                    status=item.status,
                )
            )

        if cache_updated:
            self.db.commit()

        return ExplorationAssetsResponse(assets=assets)
