#!/usr/bin/env python3
"""
Debug script to test ImageCollection.median() optimization with detailed logging
"""

import logging
import time
import sys
import os

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_median_optimization():
    logger.info("🔍 === TESTING MEDIAN OPTIMIZATION ===")
    
    try:
        # Test VAE service directly
        from app.services.vae_service import VAEService
        from app.db.session import SessionLocal
        from sqlalchemy import text
        
        # Get test event data
        db = SessionLocal()
        try:
            fire_row = db.execute(text("""
                SELECT id, start_date, 
                       ST_Y(centroid::geometry) as lat,
                       ST_X(centroid::geometry) as lon
                FROM fire_events
                WHERE id = 'eee06dee-f626-4c4e-a1da-12bb3a4d3480'
            """)).fetchone()
            
            if not fire_row:
                logger.error("❌ Test event not found")
                return
                
            event_id, fire_date, lat, lon = fire_row
            logger.info(f"📍 Testing event: {event_id}")
            logger.info(f"📍 Location: {lat:.4f}, {lon:.4f}")
            logger.info(f"📍 Fire date: {fire_date}")
            
        finally:
            db.close()
        
        # Create bbox
        bbox = {
            'min_lon': lon - 0.01,
            'max_lon': lon + 0.01,
            'min_lat': lat - 0.01,
            'max_lat': lat + 0.01,
        }
        
        # Test VAE service
        vae = VAEService()
        
        # Test baseline NDVI
        logger.info("📊 Testing baseline NDVI...")
        start_time = time.time()
        try:
            baseline = vae._get_baseline_ndvi(bbox, fire_date)
            baseline_time = time.time() - start_time
            logger.info(f"✅ Baseline NDVI: {baseline:.4f} (took {baseline_time:.2f}s)")
        except Exception as e:
            logger.error(f"❌ Baseline NDVI failed: {e}")
            return
        
        # Test current NDVI with median
        logger.info("📊 Testing current NDVI with median optimization...")
        start_time = time.time()
        try:
            current = vae._get_current_ndvi(bbox, fire_date)  # Use same date for testing
            current_time = time.time() - start_time
            logger.info(f"✅ Current NDVI: {current:.4f} (took {current_time:.2f}s)")
        except Exception as e:
            logger.error(f"❌ Current NDVI failed: {e}")
            return
        
        # Calculate recovery
        if baseline > 0:
            recovery_pct = max(0, min(100, (current / baseline) * 100))
            logger.info(f"📈 Recovery percentage: {recovery_pct:.1f}%")
        
        logger.info("🎉 === MEDIAN OPTIMIZATION TEST COMPLETED ===")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_median_optimization()
