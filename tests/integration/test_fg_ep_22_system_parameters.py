from datetime import datetime, timedelta, timezone
from uuid import uuid4

from geoalchemy2.elements import WKTElement
from sqlalchemy import bindparam, text

from app.models.fire import FireEvent
from app.schemas.fire import FireStatus
from app.services.fire_service import FireService


CANONICAL_KEYS = [
    "event_spatial_epsilon_meters",
    "event_temporal_window_hours",
    "event_monitoring_window_hours",
    "episode_spatial_epsilon_meters",
    "episode_temporal_window_hours",
]


def test_canonical_system_parameter_keys_exist(db_session):
    rows = db_session.execute(
        text(
            """
            SELECT param_key
            FROM public.system_parameters
            WHERE param_key IN :keys
            ORDER BY param_key
            """
        ).bindparams(bindparam("keys", expanding=True)),
        {"keys": tuple(CANONICAL_KEYS)},
    ).fetchall()

    found = {row[0] for row in rows}
    assert found == set(CANONICAL_KEYS)


def test_fire_status_recency_uses_event_monitoring_window_hours(db_session):
    db_session.execute(
        text(
            """
            UPDATE public.system_parameters
               SET param_value = '{"value": 1, "unit": "hours"}'::jsonb
             WHERE param_key = 'event_monitoring_window_hours'
            """
        )
    )

    service = FireService(db_session)
    fire = FireEvent(
        id=uuid4(),
        start_date=datetime.now(timezone.utc) - timedelta(days=1),
        end_date=datetime.now(timezone.utc) - timedelta(hours=2),
        last_seen_at=datetime.now(timezone.utc) - timedelta(hours=2),
        total_detections=1,
        province="Test",
        centroid=WKTElement("POINT(0 0)", srid=4326),
        status=None,
    )

    assert service.resolve_fire_status(fire) == FireStatus.EXTINCT
