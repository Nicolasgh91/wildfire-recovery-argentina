from datetime import datetime, timedelta, timezone
from uuid import uuid4

import numpy as np

import app.services.detection_clustering_service as dcs_module
from app.services.detection_clustering_service import (
    ClusteringVersion,
    DetectionClusteringService,
    DetectionRow,
)


class _DummyResult:
    def __init__(self, scalar_value=None):
        self._scalar_value = scalar_value

    def scalar(self):
        return self._scalar_value


class _RecordingSession:
    def __init__(self):
        self.calls = []

    def execute(self, statement, params=None):
        self.calls.append((str(statement), params))
        return _DummyResult()


def test_insert_event_sets_last_seen_at_to_cluster_max_detected_at():
    event_id = uuid4()
    now = datetime(2026, 2, 13, 10, 0, tzinfo=timezone.utc)
    cluster = [
        DetectionRow(
            id=uuid4(),
            detected_at=now,
            lat=-34.6,
            lon=-58.4,
            frp=12.3,
            confidence=60.0,
        ),
        DetectionRow(
            id=uuid4(),
            detected_at=now + timedelta(minutes=45),
            lat=-34.61,
            lon=-58.41,
            frp=30.0,
            confidence=85.0,
        ),
    ]

    calls = []

    class _InsertSession:
        def execute(self, statement, params=None):
            calls.append((str(statement), params))
            return _DummyResult(event_id)

    service = DetectionClusteringService(_InsertSession())
    inserted_id = service._insert_event(
        cluster=cluster,
        clustering_version_id=uuid4(),
        supports_h3=False,
        supports_version=False,
        h3_resolution=8,
    )

    assert inserted_id == event_id
    assert calls, "Expected at least one SQL execution"
    insert_sql, payload = calls[0]
    assert "last_seen_at" in insert_sql
    assert payload["last_seen_at"] == cluster[1].detected_at


def test_run_clustering_updates_last_seen_at_with_greatest(monkeypatch):
    db = _RecordingSession()
    service = DetectionClusteringService(db)
    event_id = uuid4()

    now = datetime(2026, 2, 13, 8, 0, tzinfo=timezone.utc)
    detections = [
        DetectionRow(
            id=uuid4(),
            detected_at=now,
            lat=-34.6,
            lon=-58.4,
            frp=12.0,
            confidence=70.0,
        ),
        DetectionRow(
            id=uuid4(),
            detected_at=now + timedelta(hours=1),
            lat=-34.6005,
            lon=-58.4005,
            frp=14.0,
            confidence=75.0,
        ),
    ]

    monkeypatch.setattr(
        service,
        "_get_active_version",
        lambda: ClusteringVersion(
            id=uuid4(),
            epsilon_km=1.0,
            min_points=2,
            temporal_window_hours=24,
            algorithm="ST-DBSCAN",
        ),
    )
    monkeypatch.setattr(service, "_fetch_pending_detections", lambda **_: detections)
    monkeypatch.setattr(
        service,
        "_cluster_labels",
        lambda *_args, **_kwargs: np.array([0, 0], dtype=int),
    )
    monkeypatch.setattr(service, "_get_fire_event_columns", lambda: set())
    monkeypatch.setattr(service, "_insert_event", lambda **_: event_id)
    monkeypatch.setattr(
        dcs_module,
        "load_canonical_episode_flow_parameters",
        lambda _db: {
            "event_spatial_epsilon_meters": 2000.0,
            "event_temporal_window_hours": 48,
            "event_monitoring_window_hours": 168,
            "episode_spatial_epsilon_meters": 6000.0,
            "episode_temporal_window_hours": 96,
        },
    )

    result = service.run_clustering(days_back=2)

    assert result["events_created"] == 1
    assert result["detections_processed"] == 2
    assert any(
        "GREATEST(last_seen_at, :detected_at)" in sql for sql, _ in db.calls
    ), "Expected last_seen_at update with GREATEST()"
