from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    event_id = db.execute(text("SELECT fire_event_id FROM vegetation_monitoring ORDER BY created_at DESC LIMIT 1")).scalar()
    print(f"Latest event ID: {event_id}")
finally:
    db.close()
