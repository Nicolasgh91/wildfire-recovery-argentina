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

# Episodes that currently have thumbnails
existing_thumb_episodes = [
    '161089a3-f7ed-45ff-96b8-10587befeda9',
    'ab5c9789-df61-4119-a5f0-055955f9ae46',
    'a3f5cb49-f852-4a0e-9487-0e64ecdcf62c',
    'de4fdb02-33f4-4dc2-bcd5-60347c9d4cf1',
    '70e1b387-8456-41fa-9533-b1937c80fb19'
]

db = SessionLocal()
try:
    # Check structure of audit_events table
    structure_query = text('''
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns 
        WHERE table_name = 'audit_events'
        ORDER BY ordinal_position
    ''')
    columns = db.execute(structure_query).mappings().all()
    
    print('audit_events table structure:')
    for col in columns:
        print(f'  {col.column_name}: {col.data_type} (nullable: {col.is_nullable})')
    
    print()
    
    # Check for recent audit events related to episodes or fire events
    placeholders = ','.join([f"'{ep_id}'" for ep_id in existing_thumb_episodes])
    like_conditions = ','.join([f"'%{ep_id}%'" for ep_id in existing_thumb_episodes])
    
    audit_query = text(f'''
        SELECT * FROM audit_events 
        WHERE (entity_id IN ({placeholders}) 
               OR details::text LIKE ANY(ARRAY[{like_conditions}]))
        ORDER BY created_at DESC 
        LIMIT 20
    ''')
    
    audit_records = db.execute(audit_query).mappings().all()
    
    print(f'Found {len(audit_records)} audit records for episodes with thumbnails:')
    for record in audit_records:
        print(f'  {record.created_at}: {record.action} - {record.entity_type} - {record.entity_id}')
        if record.details:
            print(f'    Details: {record.details}')
        print()
        
finally:
    db.close()
