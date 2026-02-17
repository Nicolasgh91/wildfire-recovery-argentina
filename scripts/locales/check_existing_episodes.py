import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import text

# Add project root to path
PROJECT_ROOT = Path('.').resolve()
sys.path.append(str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / '.env')

from app.db.session import SessionLocal

# Episodes that currently have thumbnails in carousel
existing_thumb_episodes = [
    '161089a3-f7ed-45ff-96b8-10587befeda9',
    'ab5c9789-df61-4119-a5f0-055955f9ae46',
    'a3f5cb49-f852-4a0e-9487-0e64ecdcf62c',
    'de4fdb02-33f4-4dc2-bcd5-60347c9d4cf1',
    '70e1b387-8456-41fa-9533-b1937c80fb19'
]

db = SessionLocal()
try:
    # Check how these episodes have fire events
    placeholders = ','.join([f"'{ep_id}'" for ep_id in existing_thumb_episodes])
    query = text(f'''
        SELECT fe.id as episode_id, fe.status as episode_status, fe.gee_candidate,
               f.id as fire_event_id, f.status as fire_status,
               jsonb_array_length(fe.slides_data) as slide_count,
               COUNT(fee.event_id) as linked_events
        FROM fire_episodes fe
        LEFT JOIN fire_events f ON fe.id = f.id
        LEFT JOIN fire_episode_events fee ON fe.id = fee.episode_id
        WHERE fe.id IN ({placeholders})
        GROUP BY fe.id, fe.status, fe.gee_candidate, f.id, f.status, fe.slides_data
        ORDER BY fe.id
    ''')
    
    result = db.execute(query).mappings().all()
    
    print('Existing thumbnail episodes analysis:')
    print('=' * 80)
    
    for row in result:
        has_fire_event = 'YES' if row.fire_event_id else 'NO'
        has_thumbs = 'YES' if row.slide_count and row.slide_count > 0 else 'NO'
        has_linked_events = 'YES' if row.linked_events > 0 else 'NO'
        
        print(f'Episode: {row.episode_id}')
        print(f'  Same ID Fire Event: {has_fire_event} ({row.fire_event_id})')
        print(f'  Linked Events: {has_linked_events} (count: {row.linked_events})')
        print(f'  GEE Candidate: {row.gee_candidate}')
        print(f'  Has Thumbnails: {has_thumbs}')
        print()
        
finally:
    db.close()
