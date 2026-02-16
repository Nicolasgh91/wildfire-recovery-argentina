import workers.tasks.geo_enrichment as geo_enrichment_module


class DummySession:
    def __init__(self):
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def test_geo_enrichment_skips_when_fire_events_table_is_missing(monkeypatch):
    db = DummySession()
    monkeypatch.setattr(geo_enrichment_module, "SessionLocal", lambda: db)
    monkeypatch.setattr(
        geo_enrichment_module,
        "_table_exists",
        lambda _db, table_name: table_name != "fire_events",
    )

    result = geo_enrichment_module.enrich_recent_fire_events.run(
        lookback_hours=24,
        max_events=100,
    )

    assert result["success"] is True
    assert result["skipped"] is True
    assert result["reason"] == "fire_events table missing"
    assert db.committed is False
    assert db.closed is True


def test_geo_enrichment_returns_incremental_metrics(monkeypatch):
    db = DummySession()
    monkeypatch.setattr(geo_enrichment_module, "SessionLocal", lambda: db)
    monkeypatch.setattr(geo_enrichment_module, "_table_exists", lambda *_: True)
    monkeypatch.setattr(
        geo_enrichment_module,
        "_select_candidate_event_ids",
        lambda *_: ["e1", "e2", "e3"],
    )
    monkeypatch.setattr(
        geo_enrichment_module,
        "_update_missing_provinces",
        lambda *_: 2,
    )
    monkeypatch.setattr(
        geo_enrichment_module,
        "_upsert_protected_area_intersections",
        lambda *_: 5,
    )
    monkeypatch.setattr(
        geo_enrichment_module,
        "_mark_events_as_legally_analyzed",
        lambda *_: 3,
    )

    result = geo_enrichment_module.enrich_recent_fire_events.run(
        lookback_hours=48,
        max_events=500,
    )

    assert result["success"] is True
    assert result["skipped"] is False
    assert result["candidate_events"] == 3
    assert result["province_updated"] == 2
    assert result["intersections_upserted"] == 5
    assert result["legal_analysis_marked"] == 3
    assert result["lookback_hours"] == 48
    assert result["max_events"] == 500
    assert db.committed is True
    assert db.closed is True
