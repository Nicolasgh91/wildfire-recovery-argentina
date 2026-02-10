import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from zoneinfo import ZoneInfo

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

ARG_TZ = ZoneInfo("America/Argentina/Buenos_Aires")


class ExchangeRateError(Exception):
    pass


@dataclass(frozen=True)
class ExchangeRate:
    rate: Decimal
    fetched_at: datetime
    source_url: str


_cache_lock = asyncio.Lock()
_cached_rate: Optional[ExchangeRate] = None


def _normalize_decimal(value: str) -> Decimal:
    cleaned = value.replace(".", "").replace(",", ".")
    return Decimal(cleaned)


def _extract_bna_rate(html: str) -> Decimal:
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)

    patterns = [
        r"D[oó]lar U\.?S\.?A\.?\s+([\d.,]+)\s+([\d.,]+)",
        r"D[oó]lar U\$S\s+([\d.,]+)\s+([\d.,]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            venta = match.group(2)
            return _normalize_decimal(venta)

    raise ExchangeRateError("Unable to parse USD/ARS rate from Banco Nacion page")


def _fetch_bna_rate_sync() -> Decimal:
    if not settings.BNA_EXCHANGE_RATE_URL:
        raise ExchangeRateError("BNA_EXCHANGE_RATE_URL is not configured")

    response = requests.get(
        settings.BNA_EXCHANGE_RATE_URL,
        headers={"User-Agent": "ForestGuard/1.0"},
        timeout=10,
    )
    response.raise_for_status()
    return _extract_bna_rate(response.text)


async def get_bna_usd_ars_rate(force_refresh: bool = False) -> ExchangeRate:
    global _cached_rate
    today = datetime.now(ARG_TZ).date()

    async with _cache_lock:
        if (
            not force_refresh
            and _cached_rate
            and _cached_rate.fetched_at.astimezone(ARG_TZ).date() == today
        ):
            return _cached_rate

        try:
            rate = await asyncio.to_thread(_fetch_bna_rate_sync)
            _cached_rate = ExchangeRate(
                rate=rate,
                fetched_at=datetime.now(ARG_TZ),
                source_url=settings.BNA_EXCHANGE_RATE_URL,
            )
            return _cached_rate
        except Exception as exc:
            if _cached_rate and (
                datetime.now(ARG_TZ) - _cached_rate.fetched_at < timedelta(days=1)
            ):
                logger.warning(
                    "Using cached USD/ARS rate from %s due to error: %s",
                    _cached_rate.fetched_at.isoformat(),
                    exc,
                )
                return _cached_rate
            logger.error("Failed to fetch USD/ARS rate from Banco Nacion: %s", exc)
            raise
