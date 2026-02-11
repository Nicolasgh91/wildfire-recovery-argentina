from datetime import datetime, timezone
from decimal import Decimal

from app.api.v1 import audit as audit_module


def test_normalize_text_removes_accents_and_case():
    assert audit_module._normalize_text("Chubut ") == "chubut"
    assert audit_module._normalize_text("PARQUE Nacional") == "parque nacional"


def test_build_episode_items_casts_fields():
    now = datetime.now(timezone.utc)
    rows = [
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "start_date": now,
            "end_date": now,
            "status": "closed",
            "provinces": ["Chubut"],
            "estimated_area_hectares": Decimal("12.5"),
            "detection_count": 3,
            "frp_max": Decimal("42.2"),
        }
    ]

    items = audit_module._build_episode_items(rows)
    assert len(items) == 1
    item = items[0]
    assert str(item.id) == "00000000-0000-0000-0000-000000000001"
    assert item.estimated_area_hectares == 12.5
    assert item.detection_count == 3
    assert item.frp_max == 42.2
