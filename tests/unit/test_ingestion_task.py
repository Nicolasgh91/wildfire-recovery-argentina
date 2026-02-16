from datetime import date
import sys
import types

import workers.tasks.ingestion as ingestion_module


def test_download_firms_daily_runs_real_pipeline_wrapper(monkeypatch):
    calls: list[tuple[int, bool]] = []

    def _fake_pipeline(*, days: int, dry_run: bool):
        calls.append((days, dry_run))
        return {
            "success": True,
            "records_inserted": 11,
            "duplicates_found": 3,
            "total_filtered": 14,
            "events_created": 5,
            "areas_calculated": 2,
            "intersections": 1,
            "date": date.today().isoformat(),
        }

    fake_module = types.SimpleNamespace(run_incremental_pipeline=_fake_pipeline)
    monkeypatch.setitem(sys.modules, "scripts.load_firms_incremental", fake_module)

    result = ingestion_module.download_firms_daily.run(days=3, dry_run=True)

    assert calls == [(3, True)]
    assert result["success"] is True
    assert result["records_inserted"] == 11
    assert result["duplicates_found"] == 3
    assert result["total_filtered"] == 14
    assert result["events_created"] == 5
    assert result["areas_calculated"] == 2
    assert result["intersections"] == 1
    assert result["dry_run"] is True
    assert result["source"] == "scripts.load_firms_incremental.run_incremental_pipeline"
    assert "timestamp" in result
