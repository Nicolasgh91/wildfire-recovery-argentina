from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    # Count total eligible events (2015-2025 with centroid)
    total_events = db.execute(text("""
        SELECT count(*) FROM fire_events 
        WHERE start_date >= '2015-01-01' 
        AND start_date <= '2025-10-31'
        AND centroid IS NOT NULL
    """)).scalar()
    
    # Count by year for planning
    events_by_year = db.execute(text("""
        SELECT EXTRACT(YEAR FROM start_date) as year, count(*) as count
        FROM fire_events 
        WHERE start_date >= '2015-01-01' 
        AND start_date <= '2025-10-31'
        AND centroid IS NOT NULL
        GROUP BY EXTRACT(YEAR FROM start_date)
        ORDER BY year
    """)).fetchall()
    
    print(f"Total eligible events (2015-2025): {total_events}")
    print("Events by year:")
    for year, count in events_by_year:
        print(f"  {int(year)}: {count}")
        
    # Get sample events for testing
    sample_events = db.execute(text("""
        SELECT id, province, start_date, 
               ST_AsText(ST_Centroid(centroid)) as centroid_text
        FROM fire_events 
        WHERE centroid IS NOT NULL 
        AND start_date >= '2015-01-01'
        ORDER BY start_date DESC 
        LIMIT 5
    """)).fetchall()
    
    print("\nSample events:")
    for event in sample_events:
        print(f"  ID: {str(event[0])[:8]}... | Province: {event[1]} | Date: {event[2]}")
        
finally:
    db.close()
