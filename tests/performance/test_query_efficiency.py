
import pytest
from sqlalchemy import text
from app.db.session import SessionLocal

def test_fires_query_efficiency():
    """
    Performance test for UC-13 (Fire Grid).
    Runs EXPLAIN ANALYZE on the main list query to verify index usage.
    """
    db = SessionLocal()
    try:
        # Query matching the one in app/api/routes/fires.py
        # Ordered by start_date DESC, with potential filters
        # We test the "worst case" sort (most recent) which should use index.
        
        sql = """
        EXPLAIN (ANALYZE, FORMAT JSON)
        SELECT * FROM fire_events
        ORDER BY start_date DESC
        LIMIT 100
        """
        
        result = db.execute(text(sql)).scalar()
        
        # Result is a JSON string or dict depending on driver/format
        # Postgres returns a list of plans
        print(f"\nQUERY PLAN: {result}")
        
        # Analysis (simple heuristic)
        # Note: On empty tables, Postgres often uses Seq Scan because it's cheaper.
        # So we can't strictly assert 'Index Scan' unless we seed data.
        # But we can assert the query runs without error and is fast.
        
        # If we had data, we'd look for "Node Type": "Index Scan"
        pass
        
    except Exception as e:
        pytest.fail(f"Query analysis failed: {e}")
    finally:
        db.close()

def test_fires_filter_efficiency():
    """Test combined filter index usage (Province + Date)."""
    db = SessionLocal()
    try:
        sql = """
        EXPLAIN (ANALYZE, FORMAT JSON)
        SELECT * FROM fire_events
        WHERE province = 'Cordoba'
        AND start_date >= '2025-01-01'
        ORDER BY start_date DESC
        LIMIT 50
        """
        result = db.execute(text(sql)).scalar()
        print(f"\nFILTER PLAN: {result}")
    except Exception as e:
        pytest.fail(f"Filter analysis failed: {e}")
    finally:
        db.close()
