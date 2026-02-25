from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    print("Adding UNIQUE constraint to vegetation_monitoring...")
    db.execute(text('ALTER TABLE vegetation_monitoring ADD CONSTRAINT uq_vm_event_date UNIQUE (fire_event_id, monitoring_date)'))
    
    print("Adding UNIQUE constraint to land_use_changes...")
    db.execute(text('ALTER TABLE land_use_changes ADD CONSTRAINT uq_luc_event_date UNIQUE (fire_event_id, change_detected_at)'))
    
    db.commit()
    print("UNIQUE constraints added successfully!")
    
except Exception as e:
    print(f"Error: {e}")
    db.rollback()
finally:
    db.close()
