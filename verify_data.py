from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    vm = db.execute(text("SELECT count(*) FROM vegetation_monitoring")).scalar()
    luc = db.execute(text("SELECT count(*) FROM land_use_changes")).scalar()
    
    # Get the specific record we just created
    record = db.execute(text("""
        SELECT fire_event_id, monitoring_date, ndvi_mean, baseline_ndvi, 
               recovery_percentage, human_activity_detected, activity_type
        FROM vegetation_monitoring 
        WHERE fire_event_id = 'eee06dee-f626-4c4e-a1da-12bb3a4d3480'
    """)).fetchone()
    
    print(f"VM: {vm}, LUC: {luc}")
    if record:
        print(f"Record: {record}")
    else:
        print("No record found")
        
finally:
    db.close()
