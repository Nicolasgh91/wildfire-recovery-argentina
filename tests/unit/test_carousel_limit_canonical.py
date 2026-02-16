import json

from sqlalchemy import text

from app.services.imagery_service import (
    ImageryService,
    resolve_carousel_home_limit,
)


def _upsert_param(db_session, key: str, value: int) -> None:
    db_session.execute(
        text(
            """
            INSERT INTO system_parameters (param_key, param_value, description, category)
            VALUES (:key, CAST(:value AS jsonb), 'test', 'general')
            ON CONFLICT (param_key)
            DO UPDATE SET param_value = EXCLUDED.param_value
            """
        ),
        {"key": key, "value": json.dumps({"value": value})},
    )


def test_carousel_limit_prefers_canonical_system_parameter(db_session):
    _upsert_param(db_session, "carousel_batch_size", 9)
    _upsert_param(db_session, "carousel_home_limit", 14)

    assert resolve_carousel_home_limit(db_session) == 14


def test_carousel_limit_falls_back_to_legacy_batch_size(db_session):
    db_session.execute(
        text("DELETE FROM system_parameters WHERE param_key = 'carousel_home_limit'")
    )
    _upsert_param(db_session, "carousel_batch_size", 8)

    assert resolve_carousel_home_limit(db_session) == 8


def test_carousel_limit_override_is_used_and_clamped(db_session):
    _upsert_param(db_session, "carousel_home_limit", 12)

    service = ImageryService(db_session)
    assert service._resolve_batch_size(override=4) == 4
    assert resolve_carousel_home_limit(db_session, override=80) == 50
