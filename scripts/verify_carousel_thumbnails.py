"""
Verify Carousel Thumbnails
==========================

This script verifies that all 20 carousel episodes have thumbnails generated
and stored in the database. It provides a summary of the carousel state.

Usage:
    python scripts/verify_carousel_thumbnails.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import text

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from app.db.session import SessionLocal

def ensure_db_url():
    """Ensure DATABASE_URL is set, assembling from components if necessary."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        host = os.getenv("DB_HOST")
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        port = os.getenv("DB_PORT", "5432")
        dbname = os.getenv("DB_NAME", "postgres")
        
        if host and user:
            from urllib.parse import quote_plus
            encoded_password = quote_plus(password) if password else ""
            db_url = f"postgresql://{user}:{encoded_password}@{host}:{port}/{dbname}"
            os.environ["DATABASE_URL"] = db_url
        else:
            print("ERROR: DATABASE_URL is not set and DB_* variables are incomplete.")
            sys.exit(1)

def main():
    ensure_db_url()
    
    print("=" * 60)
    print("CAROUSEL THUMBNAILS VERIFICATION")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        # Get the exact 20 episodes that the frontend would display
        RECENT_DAYS = 60
        query = text(f'''
            SELECT fe.id, fe.status, jsonb_array_length(fe.slides_data) as slide_count, 
                   fe.end_date, fe.gee_priority,
                   CASE fe.status
                       WHEN 'active' THEN 0
                       WHEN 'monitoring' THEN 1
                       WHEN 'extinct' THEN 2
                       WHEN 'closed' THEN 3
                       ELSE 4
                   END as status_order
            FROM fire_episodes fe
            WHERE (
                     fe.status IN ('active', 'monitoring')
                     OR (
                         fe.status IN ('extinct', 'closed')
                         AND fe.end_date >= NOW() AT TIME ZONE 'utc' - INTERVAL '{RECENT_DAYS} days'
                     )
                   )
            ORDER BY status_order,
                     fe.gee_priority DESC NULLS LAST,
                     fe.end_date DESC NULLS LAST
            LIMIT 20
        ''')
        
        result = db.execute(query).mappings().all()
        
        print(f"\nCarousel Episodes (Top 20):")
        print("-" * 60)
        
        with_thumbnails = 0
        without_thumbnails = 0
        
        for i, row in enumerate(result, 1):
            has_thumbs = row.slide_count and row.slide_count > 0
            status_icon = "✓" if has_thumbs else "✗"
            thumb_count = row.slide_count if has_thumbs else 0
            
            if has_thumbs:
                with_thumbnails += 1
            else:
                without_thumbnails += 1
            
            print(f"{i:2d}. {status_icon} {row.id}")
            print(f"     Status: {row.status}, Priority: {row.gee_priority}, Slides: {thumb_count}")
            print(f"     End Date: {row.end_date}")
            print()
        
        print("=" * 60)
        print("SUMMARY:")
        print(f"  Episodes with thumbnails: {with_thumbnails}/20")
        print(f"  Episodes without thumbnails: {without_thumbnails}/20")
        print(f"  Completion percentage: {(with_thumbnails/20)*100:.1f}%")
        
        if with_thumbnails == 20:
            print("\n🎉 SUCCESS: All carousel episodes have thumbnails!")
        else:
            print(f"\n⚠️  INCOMPLETE: {without_thumbnails} episodes still need thumbnails.")
        
        print("=" * 60)
        
        # Additional details about thumbnail storage
        if with_thumbnails > 0:
            print("\nThumbnail Details:")
            query2 = text('''
                SELECT id, jsonb_array_length(slides_data) as slide_count
                FROM fire_episodes 
                WHERE jsonb_array_length(slides_data) > 0
                ORDER BY slide_count DESC
            ''')
            thumb_details = db.execute(query2).mappings().all()
            
            for detail in thumb_details:
                print(f"  {detail.id}: {detail.slide_count} slides")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
