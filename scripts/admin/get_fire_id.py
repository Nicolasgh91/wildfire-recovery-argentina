from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    row = db.execute(text('SELECT id FROM fire_events WHERE centroid IS NOT NULL ORDER BY start_date DESC LIMIT 1')).fetchone()
    if row:
        print(row[0])
    else:
        print('None')
finally:
    db.close()
