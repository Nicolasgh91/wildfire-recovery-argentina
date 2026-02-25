from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    # Check recent vegetation monitoring records
    recent_records = db.execute(text("""
        SELECT fire_event_id, monitoring_date, recovery_percentage, 
               human_activity_detected, activity_type, created_at
        FROM vegetation_monitoring 
        WHERE created_at >= NOW() - INTERVAL '1 hour'
        ORDER BY created_at DESC
        LIMIT 10
    """)).fetchall()
    
    print(f"Recent vegetation monitoring records (last hour): {len(recent_records)}")
    for i, (event_id, date, recovery_pct, human_activity, activity_type, created_at) in enumerate(recent_records, 1):
        activity_display = activity_type or 'none'
        print(f"{i:2d}. {str(event_id)[:8]}... | {recovery_pct:5.1f}% | {activity_display:15s} | {created_at.strftime('%H:%M:%S')}")
    
    # Check GEE requests usage
    print(f"\nTotal vegetation_monitoring records: {db.execute(text('SELECT count(*) FROM vegetation_monitoring')).scalar()}")
    print(f"Total land_use_changes records: {db.execute(text('SELECT count(*) FROM land_use_changes')).scalar()}")
    
    # Get recovery percentage distribution
    recovery_dist = db.execute(text("""
        SELECT 
            CASE 
                WHEN recovery_percentage >= 90 THEN '90-100%'
                WHEN recovery_percentage >= 75 THEN '75-89%'
                WHEN recovery_percentage >= 50 THEN '50-74%'
                ELSE '<50%'
            END as range,
            count(*) as count
        FROM vegetation_monitoring
        WHERE created_at >= NOW() - INTERVAL '1 hour'
        GROUP BY range
        ORDER BY range DESC
    """)).fetchall()
    
    print(f"\nRecovery distribution (last hour):")
    for range_val, count in recovery_dist:
        print(f"  {range_val}: {count} events")
        
finally:
    db.close()
