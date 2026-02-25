"""Verifica las URLs almacenadas en slides_data."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from dotenv import load_dotenv; load_dotenv()
from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    rows = db.execute(text(
        "SELECT id, slides_data FROM fire_episodes "
        "WHERE slides_data IS NOT NULL AND jsonb_array_length(slides_data) > 0 "
        "LIMIT 3"
    )).mappings().all()
    for row in rows:
        print(f"\nEpisode {row['id']}:")
        for slide in row['slides_data']:
            url = slide.get('url') or slide.get('thumbnail_url') or slide.get('r2_url') or str(slide)[:120]
            print(f"  {url}")
finally:
    db.close()
