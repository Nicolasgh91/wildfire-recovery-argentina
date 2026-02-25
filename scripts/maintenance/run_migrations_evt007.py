"""Migration EVT-007: extinct_at en fire_episodes + event_extinction_window_hours."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from dotenv import load_dotenv; load_dotenv()
from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    db.execute(text("ALTER TABLE fire_episodes ADD COLUMN IF NOT EXISTS extinct_at TIMESTAMPTZ"))
    r = db.execute(text("UPDATE fire_episodes SET extinct_at = updated_at WHERE status = 'extinct' AND extinct_at IS NULL"))
    print("Backfill extinct_at:", r.rowcount, "filas")

    db.execute(text("""
        INSERT INTO system_parameters (param_key, param_value)
        VALUES ('event_extinction_window_hours', '{"unit": "hours", "value": 336}')
        ON CONFLICT (param_key) DO NOTHING
    """))
    print("system_parameters: event_extinction_window_hours insertado")

    db.commit()
    print("COMMIT OK")

    col = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='fire_episodes' AND column_name='extinct_at'")).fetchone()
    print("extinct_at existe:", col is not None)
    sp = db.execute(text("SELECT param_key, param_value FROM system_parameters WHERE param_key='event_extinction_window_hours'")).fetchone()
    print("param:", sp)
except Exception as e:
    db.rollback()
    print("ERROR:", e)
    sys.exit(1)
finally:
    db.close()
