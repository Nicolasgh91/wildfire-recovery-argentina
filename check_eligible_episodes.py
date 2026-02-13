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

# Target episodes that need thumbnails
target_episodes = [
    '2bda1681-f5fa-4fe4-ab0c-65e76ca291c7',
    '7a13787c-2b58-4cbf-8888-82023072e918', 
    '27748987-9d32-49be-ad82-b067ec69aa14',
    'ceb2fed5-144e-48d6-be36-a49976e76bd4',
    'cea11d48-cedf-44e2-ae2a-9f27bdd39830',
    '733492b5-8639-41b1-a5f0-4130b4f8c7e8',
    'ab63e46d-081f-4adc-95cf-ed269c36256d',
    'd1cfe73e-f2ca-44ef-962b-cff829fce8e9',
    'a2cad079-5aeb-421a-a3c0-921f398afe9c',
    '9f9cffba-8722-482b-a77b-b617ee1ebe8e',
    '92aa64e3-2411-4664-b378-a89843c3473e',
    '7bf8bea3-502e-4fc6-b327-34fd209d87fd',
    'b1009131-1e39-42cd-a5ba-03e832fcd401',
    'f58f9cba-3c59-4a8c-adf7-cdf929d6f383',
    '4714ae26-d222-4d9f-98ca-fab700918740'
]

db = SessionLocal()
try:
    # Check which target episodes have corresponding fire events
    placeholders = ','.join([f"'{ep_id}'" for ep_id in target_episodes])
    query = text(f'''
        SELECT fe.id as episode_id, fe.status as episode_status, fe.gee_candidate,
               f.id as fire_event_id, f.status as fire_status,
               jsonb_array_length(fe.slides_data) as slide_count
        FROM fire_episodes fe
        LEFT JOIN fire_events f ON fe.id = f.id
        WHERE fe.id IN ({placeholders})
        ORDER BY fe.gee_priority DESC NULLS LAST, fe.end_date DESC NULLS LAST
    ''')
    
    result = db.execute(query).mappings().all()
    
    print('Target episodes with fire event mapping:')
    print('=' * 80)
    eligible_episodes = []
    
    for row in result:
        has_fire_event = 'YES' if row.fire_event_id else 'NO'
        has_thumbs = 'YES' if row.slide_count and row.slide_count > 0 else 'NO'
        can_process = 'YES' if row.fire_event_id and row.gee_candidate else 'NO'
        
        print(f'Episode: {row.episode_id}')
        print(f'  Fire Event: {has_fire_event} ({row.fire_event_id})')
        print(f'  GEE Candidate: {row.gee_candidate}')
        print(f'  Has Thumbnails: {has_thumbs}')
        print(f'  Can Process: {can_process}')
        print()
        
        if can_process == 'YES' and has_thumbs == 'NO':
            eligible_episodes.append(row.episode_id)
    
    print('=' * 80)
    print(f'Episodes eligible for thumbnail generation: {len(eligible_episodes)}')
    for ep in eligible_episodes:
        print(f'  {ep}')
        
finally:
    db.close()
