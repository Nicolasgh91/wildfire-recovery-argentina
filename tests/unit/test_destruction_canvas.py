from types import SimpleNamespace

import workers.tasks.destruction as destruction_module


class DummySignature:
    def __init__(self, name, args=(), kwargs=None):
        self.name = name
        self.args = args
        self.kwargs = kwargs or {}
        self.options = {}

    def set(self, **kwargs):
        self.options.update(kwargs)
        return self


def test_generate_destruction_report_uses_chord_without_blocking(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        destruction_module,
        "detect_destruction",
        SimpleNamespace(s=lambda *args, **kwargs: DummySignature("detect", args, kwargs)),
    )
    monkeypatch.setattr(
        destruction_module,
        "classify_land_use",
        SimpleNamespace(s=lambda *args, **kwargs: DummySignature("classify", args, kwargs)),
    )
    monkeypatch.setattr(
        destruction_module,
        "compose_destruction_report",
        SimpleNamespace(s=lambda *args, **kwargs: DummySignature("compose", args, kwargs)),
    )

    def fake_group(*signatures):
        captured["signatures"] = signatures
        return {"signatures": signatures}

    def fake_chord(header, body):
        captured["header"] = header
        captured["body"] = body
        return SimpleNamespace(
            apply_async=lambda: SimpleNamespace(id="workflow-destruction-1")
        )

    monkeypatch.setattr(destruction_module, "group", fake_group)
    monkeypatch.setattr(destruction_module, "chord", fake_chord)

    result = destruction_module.generate_destruction_report.run("fire-123")

    assert result["status"] == "queued"
    assert result["workflow_id"] == "workflow-destruction-1"
    assert result["fire_event_id"] == "fire-123"
    assert len(captured["signatures"]) == 2


def test_compose_destruction_report_merges_chord_payload():
    output = destruction_module.compose_destruction_report.run(
        [
            {"destruction_detected": True, "confidence": 0.9},
            {"land_use_classes": {"bosque_nativo": {"percentage": 60}}},
        ],
        fire_event_id="fire-456",
        report_date="2026-02-16T00:00:00Z",
    )

    assert output["fire_event_id"] == "fire-456"
    assert output["report_type"] == "judicial_destruction"
    assert output["destruction"]["destruction_detected"] is True
    assert "land_use_classes" in output["land_use"]
