from types import SimpleNamespace

import workers.tasks.recovery as recovery_module


class DummySignature:
    def __init__(self, args=(), kwargs=None):
        self.args = args
        self.kwargs = kwargs or {}
        self.options = {}

    def set(self, **kwargs):
        self.options.update(kwargs)
        return self


def test_batch_recovery_analysis_uses_group_canvas(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        recovery_module,
        "analyze_recovery",
        SimpleNamespace(s=lambda *args, **kwargs: DummySignature(args, kwargs)),
    )

    def fake_group(signatures):
        captured["signatures"] = signatures
        return SimpleNamespace(apply_async=lambda: SimpleNamespace(id="group-xyz"))

    monkeypatch.setattr(recovery_module, "group", fake_group)

    result = recovery_module.batch_recovery_analysis.run(
        ["fire-1", "fire-2"],
        months_list=[3, 6],
    )

    assert result["status"] == "queued"
    assert result["group_id"] == "group-xyz"
    assert result["fire_events"] == 2
    assert result["total_tasks_enqueued"] == 4
    assert len(captured["signatures"]) == 4


def test_batch_recovery_analysis_handles_empty_input(monkeypatch):
    monkeypatch.setattr(
        recovery_module,
        "analyze_recovery",
        SimpleNamespace(s=lambda *args, **kwargs: DummySignature(args, kwargs)),
    )
    monkeypatch.setattr(
        recovery_module,
        "group",
        lambda signatures: SimpleNamespace(apply_async=lambda: SimpleNamespace(id="x")),
    )

    result = recovery_module.batch_recovery_analysis.run([], months_list=[3])

    assert result["status"] == "queued"
    assert result["group_id"] is None
    assert result["total_tasks_enqueued"] == 0
    assert result["fire_events"] == 0
