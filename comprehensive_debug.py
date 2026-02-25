#!/usr/bin/env python3
"""
Enhanced debug script with comprehensive logging to isolate 'west' error
"""

import logging
import sys
import traceback

# Configure maximum logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_imports():
    """Test imports step by step"""
    logger.info("🔍 === TESTING IMPORTS ===")
    
    try:
        logger.info("1. Importing SessionLocal...")
        from app.db.session import SessionLocal
        logger.info("✅ SessionLocal imported")
    except Exception as e:
        logger.error(f"❌ SessionLocal import failed: {e}")
        traceback.print_exc()
        return False
    
    try:
        logger.info("2. Importing VAE service...")
        from app.services.vae_service import VAEService
        logger.info("✅ VAE service imported")
    except Exception as e:
        logger.error(f"❌ VAE service import failed: {e}")
        traceback.print_exc()
        return False
    
    try:
        logger.info("3. Importing GEE service...")
        from app.services.gee_service import GEEService
        logger.info("✅ GEE service imported")
    except Exception as e:
        logger.error(f"❌ GEE service import failed: {e}")
        traceback.print_exc()
        return False
    
    return True

def test_bbox_formats():
    """Test different bbox formats"""
    logger.info("🔍 === TESTING BBOX FORMATS ===")
    
    # Format 1: GEE format
    bbox_gee = {
        'west': -68.34,
        'south': -32.91,
        'east': -68.32,
        'north': -32.89
    }
    
    # Format 2: Min/Max format
    bbox_minmax = {
        'min_lon': -68.34,
        'max_lon': -68.32,
        'min_lat': -32.91,
        'max_lat': -32.89
    }
    
    logger.info(f"📍 GEE format bbox: {bbox_gee}")
    logger.info(f"📍 Min/Max format bbox: {bbox_minmax}")
    
    return bbox_gee, bbox_minmax

def test_gee_service_directly():
    """Test GEE service without VAE wrapper"""
    logger.info("🔍 === TESTING GEE SERVICE DIRECTLY ===")
    
    try:
        from app.services.gee_service import GEEService
        
        logger.info("Creating GEE service...")
        gee = GEEService()
        logger.info("✅ GEE service created")
        
        # Test bbox
        bbox = {
            'west': -68.34,
            'south': -32.91,
            'east': -68.32,
            'north': -32.89
        }
        
        logger.info(f"Testing with bbox: {bbox}")
        
        # Test simple collection call
        from datetime import date
        logger.info("Calling get_sentinel_collection...")
        
        collection = gee.get_sentinel_collection(
            bbox=bbox,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 15),
            max_cloud_cover=25
        )
        logger.info("✅ get_sentinel_collection successful")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ GEE service test failed: {e}")
        traceback.print_exc()
        return False

def test_vae_service_stepwise():
    """Test VAE service step by step"""
    logger.info("🔍 === TESTING VAE SERVICE STEPWISE ===")
    
    try:
        from app.services.vae_service import VAEService
        
        logger.info("Creating VAE service...")
        vae = VAEService()
        logger.info("✅ VAE service created")
        
        logger.info("Accessing GEE service...")
        gee = vae._gee
        logger.info("✅ GEE service accessed")
        
        # Test bbox
        bbox = {
            'west': -68.34,
            'south': -32.91,
            'east': -68.32,
            'north': -32.89
        }
        
        logger.info(f"Testing baseline NDVI with bbox: {bbox}")
        
        from datetime import date
        fire_date = date(2026, 2, 16)
        
        logger.info("Calling _get_baseline_ndvi...")
        baseline = vae._get_baseline_ndvi(bbox, fire_date)
        logger.info(f"✅ Baseline NDVI: {baseline}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ VAE service test failed: {e}")
        traceback.print_exc()
        return False

def test_with_real_event():
    """Test with real event data from database"""
    logger.info("🔍 === TESTING WITH REAL EVENT ===")
    
    try:
        from app.db.session import SessionLocal
        from sqlalchemy import text
        
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
                return False
                
            event_id, fire_date, lat, lon = fire_row
            logger.info(f"📍 Real event: {event_id}")
            logger.info(f"📍 Location: {lat:.4f}, {lon:.4f}")
            logger.info(f"📍 Fire date: {fire_date}")
            
        finally:
            db.close()
        
        # Create bbox in GEE format
        bbox = {
            'west': lon - 0.01,
            'east': lon + 0.01,
            'south': lat - 0.01,
            'north': lat + 0.01,
        }
        logger.info(f"📍 Created bbox: {bbox}")
        
        # Test VAE service
        from app.services.vae_service import VAEService
        vae = VAEService()
        logger.info("✅ VAE service created for real event")
        
        # Test baseline NDVI
        logger.info("📊 Testing baseline NDVI with real event...")
        baseline = vae._get_baseline_ndvi(bbox, fire_date)
        logger.info(f"✅ Baseline NDVI: {baseline:.4f}")
        
        # Test current NDVI with median optimization
        logger.info("📊 Testing current NDVI with median optimization...")
        current = vae._get_current_ndvi(bbox, fire_date)  # Use same date for testing
        logger.info(f"✅ Current NDVI: {current:.4f}")
        
        # Calculate recovery
        if baseline > 0:
            recovery_pct = max(0, min(100, (current / baseline) * 100))
            logger.info(f"📈 Recovery percentage: {recovery_pct:.1f}%")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Real event test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    logger.info("🚀 === COMPREHENSIVE DEBUG START ===")
    
    # Test 1: Imports
    if not test_imports():
        logger.error("❌ Import tests failed - stopping")
        return
    
    # Test 2: Bbox formats
    bbox_gee, bbox_minmax = test_bbox_formats()
    
    # Test 3: GEE service directly
    if not test_gee_service_directly():
        logger.error("❌ GEE service test failed - stopping")
        return
    
    # Test 4: VAE service stepwise
    if not test_vae_service_stepwise():
        logger.error("❌ VAE service test failed")
        return
    
    # Test 5: Real event
    if not test_with_real_event():
        logger.error("❌ Real event test failed")
        return
    
    logger.info("🎉 === ALL TESTS COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    main()
