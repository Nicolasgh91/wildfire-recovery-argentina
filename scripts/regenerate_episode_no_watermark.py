#!/usr/bin/env python3
"""
Regenerate a single episode with watermark disabled for testing.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.services.imagery_service import ImageryService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def regenerate_episode(episode_id: str, disable_watermark_logo: bool = False, disable_all_watermark: bool = False):
    """Regenerate a single episode with optional watermark disabling."""
    
    # Set environment variables for watermark control
    if disable_all_watermark:
        os.environ["DISABLE_WATERMARK_ALL"] = "true"
        logger.info("Disabling ALL watermark processing")
    elif disable_watermark_logo:
        os.environ["DISABLE_WATERMARK_LOGO"] = "true"
        logger.info("Disabling watermark LOGO only")
    
    db = SessionLocal()
    
    try:
        service = ImageryService(db)
        
        logger.info(f"Regenerating episode {episode_id}")
        result = service.refresh_episode(episode_id, force_refresh=True)
        
        logger.info(f"Result: {result}")
        
        if result.get("status") == "updated":
            logger.info("✅ Episode regenerated successfully")
            slides_count = result.get("slides_count", 0)
            logger.info(f"Generated {slides_count} slides")
        elif result.get("status") == "not_found":
            logger.error(f"❌ Episode {episode_id} not found")
        elif result.get("status") == "error":
            logger.error(f"❌ Error regenerating episode: {result.get('reason')}")
        else:
            logger.info(f"Episode status: {result.get('status')} - {result.get('reason')}")
            
    except Exception as e:
        logger.error(f"Failed to regenerate episode: {e}")
        raise
    finally:
        db.close()
        
        # Clean up environment variables
        os.environ.pop("DISABLE_WATERMARK_LOGO", None)
        os.environ.pop("DISABLE_WATERMARK_ALL", None)


def main():
    parser = argparse.ArgumentParser(description="Regenerate a single episode with watermark disabled")
    parser.add_argument("episode_id", help="Episode ID to regenerate")
    parser.add_argument("--disable-logo", action="store_true", help="Disable watermark logo only")
    parser.add_argument("--disable-all", action="store_true", help="Disable all watermark processing")
    
    args = parser.parse_args()
    
    if args.disable_all and args.disable_logo:
        print("ERROR: Cannot specify both --disable-all and --disable-logo")
        sys.exit(1)
    
    print("=" * 60)
    print("EPISODE REGENERATION TOOL")
    print("=" * 60)
    print(f"Episode ID: {args.episode_id}")
    
    if args.disable_all:
        print("Watermark: DISABLED (all)")
    elif args.disable_logo:
        print("Watermark: DISABLED (logo only)")
    else:
        print("Watermark: ENABLED (normal)")
    
    print("-" * 60)
    
    regenerate_episode(args.episode_id, args.disable_logo, args.disable_all)


if __name__ == "__main__":
    main()
