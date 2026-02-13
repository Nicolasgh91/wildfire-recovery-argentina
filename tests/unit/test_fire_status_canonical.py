from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.schemas.fire import FireEventListItem, FireStatus


def test_fire_status_enum_is_canonical():
    assert {status.value for status in FireStatus} == {
        "active",
        "monitoring",
        "extinct",
    }


def test_fire_status_enum_rejects_legacy_values():
    with pytest.raises(ValueError):
        FireStatus("controlled")
    with pytest.raises(ValueError):
        FireStatus("extinguished")


def test_fire_event_list_item_derives_monitoring_for_recent_end_date():
    now = datetime.now()
    item = FireEventListItem(
        id=uuid4(),
        start_date=now - timedelta(days=5),
        end_date=now - timedelta(days=1),
        total_detections=3,
    )

    assert item.status == FireStatus.MONITORING


def test_fire_event_list_item_derives_extinct_for_old_end_date():
    now = datetime.now()
    item = FireEventListItem(
        id=uuid4(),
        start_date=now - timedelta(days=60),
        end_date=now - timedelta(days=30),
        total_detections=3,
    )

    assert item.status == FireStatus.EXTINCT
