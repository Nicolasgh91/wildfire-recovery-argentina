#!/usr/bin/env python3
"""
Comprehensive pipeline diagnostic to isolate PNG corruption.
Tests each step: GEE download -> storage -> watermark -> final output.
"""

import argparse
import logging
import os
import sys
import tempfile
import urllib.request
from io import BytesIO
from pathlib import Path

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("ERROR: PIL/Pillow not available")
    sys.exit(1)

from app.db.session import SessionLocal
from app.services.gee_service import GEEService
from app.services.imagery_service import ImageryService
from app.services.storage_service import StorageService
from app.utils.watermark import apply_watermark

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_png_integrity(png_bytes: bytes, name: str) -> dict:
    """Test PNG integrity and return detailed results."""
    results = {"name": name, "errors": [], "warnings": [], "size": len(png_bytes)}
    
    try:
        # Test PIL opening
        img = Image.open(BytesIO(png_bytes))
        results["dimensions"] = img.size
        results["mode"] = img.mode
        results["format"] = img.format
        
        w, h = img.size
        results["aspect_ratio"] = w / h
        
        # Test resave capability
        try:
            test_output = BytesIO()
            img.save(test_output, format="PNG")
            results["resave_test"] = "OK"
        except Exception as e:
            results["resave_test"] = f"FAILED: {e}"
            results["errors"].append(f"Resave failed: {e}")
        
        # Test numpy conversion (the original failing test)
        try:
            import numpy as np
            arr = np.array(img)
            results["numpy_test"] = "OK"
        except Exception as e:
            results["numpy_test"] = f"FAILED: {e}"
            results["errors"].append(f"Numpy conversion failed: {e}")
        
        # Edge brightness test
        try:
            pixels = img.convert("RGB")
            left_edge = pixels.crop((0, 0, 10, h))
            right_edge = pixels.crop((w-10, 0, w, h))
            
            def get_brightness(area):
                colors = area.getcolors()
                if colors:
                    total_pixels = sum(count for count, color in colors)
                    total_brightness = sum(count * sum(color) for count, color in colors)
                    return total_brightness / (total_pixels * 3)
                return 0
            
            results["left_brightness"] = get_brightness(left_edge)
            results["right_brightness"] = get_brightness(right_edge)
            
            if results["left_brightness"] < 10:
                results["warnings"].append("Left edge too dark - possible black bar")
            if results["right_brightness"] < 10:
                results["warnings"].append("Right edge too dark - possible black bar")
                
        except Exception as e:
            results["brightness_test"] = f"FAILED: {e}"
            results["errors"].append(f"Brightness test failed: {e}")
        
    except Exception as e:
        results["errors"].append(f"Failed to open image: {e}")
    
    return results


def test_gee_download(episode_id: str) -> dict:
    """Test GEE download directly."""
    logger.info(f"Testing GEE download for episode {episode_id}")
    
    db = SessionLocal()
    try:
        service = ImageryService(db)
        episode = service._fetch_episode_by_id(episode_id)
        
        if not episode:
            return {"error": f"Episode {episode_id} not found"}
        
        if episode.lat is None or episode.lon is None:
            return {"error": "Episode missing coordinates"}
        
        # Get bbox and select image
        bbox = service._bbox_from_point(episode.lat, episode.lon)
        thresholds = service._resolve_cloud_thresholds()
        
        image, is_archive, used_threshold = service._select_image(bbox, thresholds)
        if image is None:
            return {"error": "No suitable image found"}
        
        # Download raw thumbnail without any processing
        dimensions = service._resolve_thumb_dimensions()
        resample = service._resolve_gee_resample()
        
        raw_bytes = service._download_thumbnail(
            image,
            bbox,
            vis_type="RGB",
            dimensions=dimensions,
            resample=resample,
        )
        
        return {"raw_bytes": raw_bytes, "bbox": bbox, "dimensions": dimensions}
        
    except Exception as e:
        return {"error": f"GEE download failed: {e}"}
    finally:
        db.close()


def test_storage_upload_download(png_bytes: bytes) -> dict:
    """Test storage upload and download integrity."""
    logger.info("Testing storage upload/download")
    
    storage = StorageService()
    
    try:
        # Upload to temporary location
        temp_key = f"temp-test/{Path(__file__).stem}-test.png"
        upload_result = storage.upload_bytes(
            data=png_bytes,
            key=temp_key,
            bucket=os.environ.get("STORAGE_BUCKET_IMAGES", "forestguard-images"),
            content_type="image/png",
        )
        
        if not upload_result.success:
            return {"error": f"Upload failed: {upload_result.error}"}
        
        # Download back
        downloaded_bytes = storage.download_bytes(
            key=temp_key,
            bucket=os.environ.get("STORAGE_BUCKET_IMAGES", "forestguard-images"),
        )
        
        # Clean up
        try:
            storage.delete_object(
                key=temp_key,
                bucket=os.environ.get("STORAGE_BUCKET_IMAGES", "forestguard-images"),
            )
        except Exception:
            pass  # Best effort cleanup
        
        return {"downloaded_bytes": downloaded_bytes}
        
    except Exception as e:
        return {"error": f"Storage test failed: {e}"}


def test_watermark_processing(png_bytes: bytes) -> dict:
    """Test watermark processing with different configurations."""
    logger.info("Testing watermark processing")
    
    results = {}
    
    # Test 1: Normal watermark
    os.environ.pop("DISABLE_WATERMARK_LOGO", None)
    os.environ.pop("DISABLE_WATERMARK_ALL", None)
    
    try:
        processed = apply_watermark(png_bytes)
        results["normal"] = processed
    except Exception as e:
        results["normal"] = f"FAILED: {e}"
    
    # Test 2: Logo disabled
    os.environ["DISABLE_WATERMARK_LOGO"] = "true"
    try:
        processed = apply_watermark(png_bytes)
        results["logo_disabled"] = processed
    except Exception as e:
        results["logo_disabled"] = f"FAILED: {e}"
    
    # Test 3: All disabled
    os.environ["DISABLE_WATERMARK_ALL"] = "true"
    try:
        processed = apply_watermark(png_bytes)
        results["all_disabled"] = processed
    except Exception as e:
        results["all_disabled"] = f"FAILED: {e}"
    
    # Clean up
    os.environ.pop("DISABLE_WATERMARK_LOGO", None)
    os.environ.pop("DISABLE_WATERMARK_ALL", None)
    
    return results


def diagnose_episode_pipeline(episode_id: str):
    """Run complete pipeline diagnostic for an episode."""
    print("=" * 80)
    print(f"PIPELINE CORRUPTION DIAGNOSTIC")
    print(f"Episode ID: {episode_id}")
    print("=" * 80)
    
    # Step 1: Test GEE download
    print("\n📡 STEP 1: GEE Download")
    print("-" * 40)
    
    gee_result = test_gee_download(episode_id)
    
    if "error" in gee_result:
        print(f"❌ GEE download failed: {gee_result['error']}")
        return
    
    raw_bytes = gee_result["raw_bytes"]
    print(f"✅ GEE download successful: {len(raw_bytes)} bytes")
    
    # Test raw GEE output
    raw_test = test_png_integrity(raw_bytes, "GEE Raw")
    print(f"Dimensions: {raw_test.get('dimensions')}")
    print(f"Resave test: {raw_test.get('resave_test')}")
    print(f"Numpy test: {raw_test.get('numpy_test')}")
    
    if raw_test["errors"]:
        print("❌ GEE output is CORRUPTED")
        for error in raw_test["errors"]:
            print(f"   - {error}")
        print("\n🎯 ROOT CAUSE: GEE download is producing corrupted PNGs")
        return
    else:
        print("✅ GEE output is clean")
    
    # Step 2: Test storage
    print("\n💾 STEP 2: Storage Upload/Download")
    print("-" * 40)
    
    storage_result = test_storage_upload_download(raw_bytes)
    
    if "error" in storage_result:
        print(f"❌ Storage test failed: {storage_result['error']}")
        return
    
    downloaded_bytes = storage_result["downloaded_bytes"]
    print(f"✅ Storage test successful: {len(downloaded_bytes)} bytes")
    
    # Test storage integrity
    storage_test = test_png_integrity(downloaded_bytes, "Storage Round-trip")
    print(f"Resave test: {storage_test.get('resave_test')}")
    print(f"Numpy test: {storage_test.get('numpy_test')}")
    
    if storage_test["errors"]:
        print("❌ Storage is CORRUPTING files")
        for error in storage_test["errors"]:
            print(f"   - {error}")
        print("\n🎯 ROOT CAUSE: Storage upload/download is corrupting PNGs")
        return
    else:
        print("✅ Storage round-trip is clean")
    
    # Step 3: Test watermark processing
    print("\n🎨 STEP 3: Watermark Processing")
    print("-" * 40)
    
    watermark_results = test_watermark_processing(raw_bytes)
    
    for config, result in watermark_results.items():
        print(f"\nTesting {config}:")
        
        if isinstance(result, str):
            print(f"❌ {result}")
            continue
        
        wm_test = test_png_integrity(result, f"Watermark ({config})")
        print(f"  Size: {len(result)} bytes")
        print(f"  Resave test: {wm_test.get('resave_test')}")
        print(f"  Numpy test: {wm_test.get('numpy_test')}")
        
        if wm_test["errors"]:
            print(f"❌ {config} watermark is CORRUPTING files")
            for error in wm_test["errors"]:
                print(f"     - {error}")
            
            if config == "normal":
                print("\n🎯 ROOT CAUSE: Watermark processing is corrupting PNGs")
            elif config == "logo_disabled":
                print("\n🎯 ROOT CAUSE: Watermark text/metadata is corrupting PNGs")
        else:
            print(f"✅ {config} watermark is clean")
    
    print("\n" + "=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Diagnose PNG corruption in the pipeline")
    parser.add_argument("episode_id", help="Episode ID to test")
    
    args = parser.parse_args()
    
    diagnose_episode_pipeline(args.episode_id)


if __name__ == "__main__":
    main()
