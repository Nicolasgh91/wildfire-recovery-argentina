#!/usr/bin/env python3
"""
Regenerate the problematic episode with the PNG corruption fix.
"""

import sys
from pathlib import Path

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.services.imagery_service import ImageryService

def regenerate_episode(episode_id: str):
    """Regenerate episode with PNG corruption fix."""
    
    print(f"Regenerating episode {episode_id} with PNG corruption fix...")
    
    db = SessionLocal()
    
    try:
        service = ImageryService(db)
        
        print("Refreshing episode...")
        result = service.refresh_episode(episode_id, force_refresh=True)
        
        print(f"Result: {result}")
        
        if result.get("status") == "updated":
            print("✅ Episode regenerated successfully!")
            slides_count = result.get("slides_count", 0)
            print(f"Generated {slides_count} slides")
            
            # Get the episode data to check new URLs
            episode = service._fetch_episode_by_id(episode_id)
            if episode and episode.slides_data:
                print("\nNew slide URLs:")
                for i, slide in enumerate(episode.slides_data):
                    url = slide.get('thumbnail_url') or slide.get('url')
                    if url:
                        print(f"  {i+1}. {slide.get('type', 'unknown')}: {url}")
            
        elif result.get("status") == "not_found":
            print(f"❌ Episode {episode_id} not found")
        elif result.get("status") == "error":
            print(f"❌ Error regenerating episode: {result.get('reason')}")
        else:
            print(f"Episode status: {result.get('status')} - {result.get('reason')}")
            
    except Exception as e:
        print(f"❌ Failed to regenerate episode: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    # Use the episode ID from the problematic URL
    episode_id = "5bd52c45-70c3-43f0-bccf-ccf7be86286c"
    regenerate_episode(episode_id)
