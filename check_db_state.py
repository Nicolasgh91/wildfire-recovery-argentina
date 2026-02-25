from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

try:
    vm_count = db.execute(text('SELECT count(*) FROM vegetation_monitoring')).scalar()
    luc_count = db.execute(text('SELECT count(*) FROM land_use_changes')).scalar()
    events_count = db.execute(text('''
        SELECT count(*) FROM fire_events 
        WHERE start_date > NOW() - INTERVAL " 36 months\
 AND centroid IS NOT NULL
 ''')).scalar()
 
 print(f'vegetation_monitoring rows: {vm_count}')
 print(f'land_use_changes rows: {luc_count}')
 print(f'Fire events eligible for VAE: {events_count}')
 
finally:
 db.close()
