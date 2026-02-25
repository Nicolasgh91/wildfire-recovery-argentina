#!/usr/bin/env python3
"""
Simple test to isolate the 'west' error
"""

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_simple():
    try:
        logger.info("Testing VAE service initialization...")
        from app.services.vae_service import VAEService
        
        vae = VAEService()
        logger.info("✅ VAE service initialized successfully")
        
        # Test with a simple bbox
        bbox = {
            'west': -68.34,
            'south': -32.91,
            'east': -68.32,
            'north': -32.89
        }
        logger.info(f"📍 Using bbox: {bbox}")
        
        # Test GEE service directly
        logger.info("Testing GEE service directly...")
        gee = vae._gee
        logger.info("✅ GEE service accessed")
        
        # Test a simple GEE call
        from datetime import date
        collection = gee.get_sentinel_collection(
            bbox=bbox,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 15),
            max_cloud_cover=25
        )
        logger.info("✅ Sentinel collection retrieved")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple()
