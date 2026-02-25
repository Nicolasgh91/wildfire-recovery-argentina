from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    # Get recent episodes for backfill (fixed SQL)
    episodes = db.execute(text("""
        SELECT ep.id, ep.status, ep.created_at,
               COUNT(fe.id) as event_count,
               CASE WHEN ep.status = 'active' THEN 1
                    WHEN ep.status = 'monitoring' THEN 2
                    ELSE 3 END as status_priority
        FROM fire_episodes ep
        JOIN fire_episode_events fee ON ep.id = fee.episode_id
        JOIN fire_events fe ON fee.event_id = fe.id
        WHERE fe.centroid IS NOT NULL
        AND fe.start_date >= NOW() - INTERVAL '12 months'
        GROUP BY ep.id, ep.status, ep.created_at
        ORDER BY status_priority, ep.created_at DESC
        LIMIT 20
    """)).fetchall()
    
    print(f"Found {len(episodes)} recent episodes:")
    for i, (ep_id, status, created_at, event_count, priority) in enumerate(episodes, 1):
        print(f"{i:2d}. {str(ep_id)[:8]}... | {status:10s} | {event_count:2d} events | {created_at}")
        
finally:
    db.close()
