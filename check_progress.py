from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    vm = db.execute(text("SELECT count(*) FROM vegetation_monitoring")).scalar()
    luc = db.execute(text("SELECT count(*) FROM land_use_changes")).scalar()
    
    print(f"📊 DATABASE PROGRESS:")
    print(f"   Vegetation Monitoring: {vm} records")
    print(f"   Land Use Changes: {luc} records")
    
    # Get recent records
    recent_vm = db.execute(text("""
        SELECT COUNT(*) FROM vegetation_monitoring 
        WHERE created_at >= NOW() - INTERVAL '1 hour'
    """)).scalar()
    
    print(f"   Recent (last hour): {recent_vm} new VM records")
    
finally:
    db.close()
