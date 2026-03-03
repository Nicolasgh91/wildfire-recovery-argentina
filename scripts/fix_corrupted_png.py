#!/usr/bin/env python3
"""
Fix corrupted PNGs by stripping problematic metadata.
"""

import sys
from pathlib import Path
from io import BytesIO
import urllib.request

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image

def fix_png_metadata(png_bytes: bytes) -> bytes:
    """Fix corrupted PNG by removing problematic metadata."""
    
    # Load image
    img = Image.open(BytesIO(png_bytes))
    
    # Create new image without metadata
    if img.mode == 'RGBA':
        new_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
        new_img.paste(img, (0, 0))
    else:
        new_img = img.convert('RGBA')
    
    # Save without metadata
    output = BytesIO()
    new_img.save(output, format='PNG', compress_level=6)
    
    return output.getvalue()

def test_fix():
    """Test the PNG fix."""
    
    url = 'https://objectstorage.us-ashburn-1.oraclecloud.com/n/idp4lzoo2ao6/b/forestguard-images/o/carousel/5bd52c45-70c3-43f0-bccf-ccf7be86286c/swir_20260208.png'
    
    print("Testing PNG fix...")
    print(f"URL: {url}")
    
    try:
        # Download corrupted image
        with urllib.request.urlopen(url) as response:
            original_data = response.read()
        
        print(f"Original size: {len(original_data)} bytes")
        
        # Test original (should fail)
        try:
            original_img = Image.open(BytesIO(original_data))
            test_output = BytesIO()
            original_img.save(test_output, format='PNG')
            print("❌ Original image saves fine (unexpected!)")
        except Exception as e:
            print(f"✅ Original image fails as expected: {e}")
        
        # Fix the image
        fixed_data = fix_png_metadata(original_data)
        print(f"Fixed size: {len(fixed_data)} bytes")
        
        # Test fixed image
        try:
            fixed_img = Image.open(BytesIO(fixed_data))
            print(f"✅ Fixed image opens: {fixed_img.size} {fixed_img.mode}")
            
            # Test save
            test_output = BytesIO()
            fixed_img.save(test_output, format='PNG')
            print(f"✅ Fixed image saves: {len(test_output.getvalue())} bytes")
            
            # Test numpy
            import numpy as np
            arr = np.array(fixed_img)
            print(f"✅ Fixed image numpy: {arr.shape}")
            
            print("✅ PNG fix successful!")
            
            # Save fixed image for comparison
            with open('fixed_swir_20260208.png', 'wb') as f:
                f.write(fixed_data)
            print("Saved as: fixed_swir_20260208.png")
            
        except Exception as e:
            print(f"❌ Fixed image still fails: {e}")
        
    except Exception as e:
        print(f"❌ Failed to test fix: {e}")

if __name__ == "__main__":
    test_fix()
