from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    # Check fire_episode_events table structure
    print("=== fire_episode_events columns ===")
    columns = db.execute(text("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'fire_episode_events' 
        ORDER BY ordinal_position
    """)).fetchall()
    
    for col in columns:
        print(f"  {col[0]}: {col[1]}")
    
    print("\n=== Sample data ===")
    sample = db.execute(text("""
        SELECT * FROM fire_episode_events 
        LIMIT 3
    """)).fetchall()
    
    for row in sample:
        print(f"  {row}")
        
finally:
    db.close()
