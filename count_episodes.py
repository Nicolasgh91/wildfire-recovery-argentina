from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    # Query principal para obtener datos reales
    result = db.execute(text("""
        SELECT 
            count(DISTINCT fe.id) as total_events,
            count(DISTINCT ep.id) as total_episodes,
            round(count(DISTINCT fe.id)::numeric / NULLIF(count(DISTINCT ep.id), 0), 1) as ratio
        FROM fire_events fe
        LEFT JOIN fire_episode_events fee ON fe.id = fee.event_id
        LEFT JOIN fire_episodes ep ON fee.episode_id = ep.id
        WHERE fe.start_date >= '2015-01-01' AND fe.centroid IS NOT NULL
    """)).fetchone()
    
    print(f"Total events (2015-2025): {result[0]}")
    print(f"Total episodes: {result[1]}")
    print(f"Events per episode ratio: {result[2]}")
    
    # Episodes por status
    status_result = db.execute(text("""
        SELECT 
            ep.status,
            count(*) as count
        FROM fire_episodes ep
        WHERE EXISTS (
            SELECT 1 FROM fire_episode_events fee 
            JOIN fire_events fe ON fee.event_id = fe.id
            WHERE fee.episode_id = ep.id 
            AND fe.start_date >= '2015-01-01' 
            AND fe.centroid IS NOT NULL
        )
        GROUP BY ep.status
        ORDER BY count DESC
    """)).fetchall()
    
    print("\nEpisodes by status:")
    for status, count in status_result:
        print(f"  {status}: {count}")
        
finally:
    db.close()
