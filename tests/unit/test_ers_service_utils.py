from datetime import date

from app.services.ers_service import ERSService


def test_resolve_report_max_images_from_dict(monkeypatch):
    service = ERSService()
    monkeypatch.setattr(service, "_get_system_param", lambda key: {"value": 8})
    assert service._resolve_report_max_images() == 8


def test_resolve_report_max_images_default(monkeypatch):
    service = ERSService()
    monkeypatch.setattr(service, "_get_system_param", lambda key: None)
    assert service._resolve_report_max_images() == 12


def test_resolve_report_image_cost(monkeypatch):
    service = ERSService()
    monkeypatch.setattr(service, "_get_system_param", lambda key: {"value": 0.75})
    assert service._resolve_report_image_cost() == 0.75


def test_infer_vis_type_from_image_type():
    service = ERSService()
    assert service._infer_vis_type("closure_dnbr", None) == "DNBR"
    assert service._infer_vis_type("closure_nbr", None) == "NBR"
    assert service._infer_vis_type("carousel", None) == "RGB"


def test_infer_vis_type_from_params():
    service = ERSService()
    assert service._infer_vis_type("", {"vis_type": "ndvi"}) == "NDVI"
    assert service._infer_vis_type("", {"bands": ["B12", "B8A", "B4"]}) == "NBR"


def test_add_months_handles_day_overflow():
    service = ERSService()
    result = service._add_months(date(2024, 1, 31), 1)
    assert result.month == 2
    assert result.day == 28


def test_create_verification_hash_is_stable():
    service = ERSService()
    hash_1 = service._create_verification_hash(b"abc")
    hash_2 = service._create_verification_hash(b"abc")
    assert hash_1 == hash_2
    assert hash_1.startswith("sha256:")
