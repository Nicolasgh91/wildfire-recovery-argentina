#!/usr/bin/env python3
"""
Diagnostic script to test PNG corruption in carousel thumbnails.
Tests both with and without watermark to isolate the issue.
"""

import argparse
import logging
import os
import sys
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

from app.utils.watermark import apply_watermark

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_png_integrity(url: str, name: str = "Unknown") -> dict:
    """Test PNG file integrity and return diagnostic results."""
    results = {"name": name, "url": url, "errors": [], "warnings": []}
    
    try:
        # Download image
        logger.info(f"Testing {name}: {url}")
        with urllib.request.urlopen(url) as response:
            data = response.read()
        
        results["file_size_kb"] = len(data) / 1024
        
        # Test PIL opening
        img = Image.open(BytesIO(data))
        results["dimensions"] = img.size
        results["mode"] = img.mode
        results["format"] = img.format
        
        w, h = img.size
        results["aspect_ratio"] = w / h
        results["expected_ratio"] = 4/3  # 1.3333...
        
        # Check aspect ratio
        if abs(results["aspect_ratio"] - results["expected_ratio"]) > 0.01:
            results["warnings"].append(f"Aspect ratio mismatch: {results['aspect_ratio']:.4f} vs {results['expected_ratio']:.4f}")
        
        # Test resave capability
        try:
            test_output = BytesIO()
            img.save(test_output, format="PNG")
            results["resave_test"] = "OK"
        except Exception as e:
            results["resave_test"] = f"FAILED: {e}"
            results["errors"].append(f"Resave failed: {e}")
        
        # Test edge brightness (detect black bars)
        try:
            pixels = img.convert("RGB")
            left_edge = pixels.crop((0, 0, 10, h))
            right_edge = pixels.crop((w-10, 0, w, h))
            center_area = pixels.crop((w//2-5, 0, w//2+5, h))
            
            def get_brightness(area):
                colors = area.getcolors()
                if colors:
                    total_pixels = sum(count for count, color in colors)
                    total_brightness = sum(count * sum(color) for count, color in colors)
                    return total_brightness / (total_pixels * 3)  # 3 channels
                return 0
            
            results["left_brightness"] = get_brightness(left_edge)
            results["right_brightness"] = get_brightness(right_edge)
            results["center_brightness"] = get_brightness(center_area)
            
            # Detect black bars
            if results["left_brightness"] < 10:
                results["warnings"].append("Left edge too dark - possible black bar")
            if results["right_brightness"] < 10:
                results["warnings"].append("Right edge too dark - possible black bar")
                
        except Exception as e:
            results["brightness_test"] = f"FAILED: {e}"
            results["errors"].append(f"Brightness test failed: {e}")
        
    except Exception as e:
        results["errors"].append(f"Failed to process image: {e}")
    
    return results


def test_watermark_processing(image_bytes: bytes) -> dict:
    """Test watermark processing with different feature flag combinations."""
    results = {"tests": []}
    
    # Test 1: Normal watermark (current behavior)
    os.environ.pop("DISABLE_WATERMARK_LOGO", None)
    os.environ.pop("DISABLE_WATERMARK_ALL", None)
    
    try:
        processed = apply_watermark(image_bytes)
        img = Image.open(BytesIO(processed))
        results["tests"].append({
            "config": "normal",
            "status": "OK",
            "size": len(processed),
            "dimensions": img.size
        })
    except Exception as e:
        results["tests"].append({
            "config": "normal",
            "status": "FAILED",
            "error": str(e)
        })
    
    # Test 2: Logo disabled
    os.environ["DISABLE_WATERMARK_LOGO"] = "true"
    
    try:
        processed = apply_watermark(image_bytes)
        img = Image.open(BytesIO(processed))
        results["tests"].append({
            "config": "logo_disabled",
            "status": "OK",
            "size": len(processed),
            "dimensions": img.size
        })
    except Exception as e:
        results["tests"].append({
            "config": "logo_disabled",
            "status": "FAILED",
            "error": str(e)
        })
    
    # Test 3: All watermark disabled
    os.environ["DISABLE_WATERMARK_ALL"] = "true"
    
    try:
        processed = apply_watermark(image_bytes)
        img = Image.open(BytesIO(processed))
        results["tests"].append({
            "config": "all_disabled",
            "status": "OK",
            "size": len(processed),
            "dimensions": img.size
        })
    except Exception as e:
        results["tests"].append({
            "config": "all_disabled",
            "status": "FAILED",
            "error": str(e)
        })
    
    # Clean up environment
    os.environ.pop("DISABLE_WATERMARK_LOGO", None)
    os.environ.pop("DISABLE_WATERMARK_ALL", None)
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Diagnose PNG corruption in carousel thumbnails")
    parser.add_argument("--url", help="Specific image URL to test")
    parser.add_argument("--test-watermark", action="store_true", help="Test watermark processing")
    parser.add_argument("--download-only", action="store_true", help="Only download and test, no watermark")
    
    args = parser.parse_args()
    
    # Default test URLs
    test_urls = [
        "https://objectstorage.us-ashburn-1.oraclecloud.com/n/idp4lzoo2ao6/b/forestguard-images/o/carousel/5bd52c45-70c3-43f0-bccf-ccf7be86286c/rgb_20260208.png",
    ]
    
    if args.url:
        test_urls = [args.url]
    
    print("=" * 80)
    print("PNG CORRUPTION DIAGNOSTIC TOOL")
    print("=" * 80)
    
    all_results = []
    
    for url in test_urls:
        result = test_png_integrity(url, f"Image {len(all_results) + 1}")
        all_results.append(result)
        
        print(f"\n--- {result['name']} ---")
        print(f"URL: {result['url']}")
        print(f"Dimensions: {result['dimensions']}")
        print(f"Aspect Ratio: {result['aspect_ratio']:.4f} (expected: {result['expected_ratio']:.4f})")
        print(f"File Size: {result['file_size_kb']:.1f} KB")
        print(f"Mode: {result['mode']}")
        print(f"Resave Test: {result['resave_test']}")
        
        if "left_brightness" in result:
            print(f"Edge Brightness - Left: {result['left_brightness']:.1f}, Center: {result['center_brightness']:.1f}, Right: {result['right_brightness']:.1f}")
        
        if result['errors']:
            print("ERRORS:")
            for error in result['errors']:
                print(f"  ❌ {error}")
        
        if result['warnings']:
            print("WARNINGS:")
            for warning in result['warnings']:
                print(f"  ⚠️  {warning}")
        
        if not result['errors'] and not result['warnings']:
            print("✅ Image appears healthy")
        
        # Test watermark processing if requested
        if args.test_watermark and not result['errors']:
            print("\n--- Watermark Processing Tests ---")
            
            # Download fresh image bytes for watermark testing
            try:
                with urllib.request.urlopen(url) as response:
                    image_bytes = response.read()
                
                watermark_results = test_watermark_processing(image_bytes)
                
                for test in watermark_results["tests"]:
                    status_icon = "✅" if test["status"] == "OK" else "❌"
                    print(f"{status_icon} {test['config']}: {test['status']}")
                    if test["status"] == "OK":
                        print(f"    Size: {test['size']} bytes, Dimensions: {test['dimensions']}")
                    else:
                        print(f"    Error: {test['error']}")
                        
            except Exception as e:
                print(f"❌ Watermark testing failed: {e}")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    total_errors = sum(len(r['errors']) for r in all_results)
    total_warnings = sum(len(r['warnings']) for r in all_results)
    
    print(f"Images tested: {len(all_results)}")
    print(f"Total errors: {total_errors}")
    print(f"Total warnings: {total_warnings}")
    
    if total_errors == 0 and total_warnings == 0:
        print("✅ All images appear healthy")
    elif total_errors > 0:
        print("❌ Critical issues found - PNG corruption detected")
    else:
        print("⚠️  Potential issues found - investigation recommended")


if __name__ == "__main__":
    main()
