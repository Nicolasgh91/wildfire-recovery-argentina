#!/usr/bin/env python3
"""
Quick test to verify watermark feature flag functionality.
"""

import os
import sys
from pathlib import Path

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.utils.watermark import apply_watermark
from PIL import Image
from io import BytesIO

def create_test_image():
    """Create a simple test image."""
    img = Image.new('RGB', (768, 576), color='blue')
    output = BytesIO()
    img.save(output, format='PNG')
    return output.getvalue()

def test_feature_flags():
    """Test watermark feature flags."""
    print("Testing Watermark Feature Flags")
    print("=" * 40)
    
    # Create test image
    test_bytes = create_test_image()
    print(f"Test image size: {len(test_bytes)} bytes")
    
    # Test 1: Normal watermark
    os.environ.pop("DISABLE_WATERMARK_LOGO", None)
    os.environ.pop("DISABLE_WATERMARK_ALL", None)
    
    result = apply_watermark(test_bytes)
    print(f"Normal watermark: {len(result)} bytes")
    
    # Test 2: Logo disabled
    os.environ["DISABLE_WATERMARK_LOGO"] = "true"
    result = apply_watermark(test_bytes)
    print(f"Logo disabled: {len(result)} bytes")
    
    # Test 3: All disabled
    os.environ["DISABLE_WATERMARK_ALL"] = "true"
    result = apply_watermark(test_bytes)
    print(f"All disabled: {len(result)} bytes")
    
    # Clean up
    os.environ.pop("DISABLE_WATERMARK_LOGO", None)
    os.environ.pop("DISABLE_WATERMARK_ALL", None)
    
    print("✅ Feature flag test completed")

if __name__ == "__main__":
    test_feature_flags()
