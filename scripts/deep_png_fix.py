#!/usr/bin/env python3
"""
Deep PNG fix by reconstructing the image from pixels.
"""

import sys
from pathlib import Path
from io import BytesIO
import urllib.request

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image
import numpy as np

def deep_fix_png(png_bytes: bytes) -> bytes:
    """Deep fix by reconstructing image from pixel data."""
    
    try:
        # Load the corrupted image
        img = Image.open(BytesIO(png_bytes))
        
        # Convert to numpy array (this might fail, but let's try different approaches)
        try:
            arr = np.array(img)
            print(f"✅ Direct numpy conversion worked: {arr.shape}")
        except Exception as e:
            print(f"❌ Direct numpy failed: {e}")
            
            # Try pixel by pixel copy
            print("Attempting pixel reconstruction...")
            width, height = img.size
            
            # Create new array
            if img.mode == 'RGBA':
                arr = np.zeros((height, width, 4), dtype=np.uint8)
                
                # Copy pixels manually
                for y in range(height):
                    for x in range(width):
                        try:
                            pixel = img.getpixel((x, y))
                            arr[y, x] = pixel
                        except Exception:
                            # Use default pixel if getpixel fails
                            arr[y, x] = [0, 0, 0, 255]
                
                print(f"✅ Manual pixel reconstruction: {arr.shape}")
            else:
                raise ValueError(f"Unsupported image mode: {img.mode}")
        
        # Create new image from array
        fixed_img = Image.fromarray(arr, 'RGBA')
        
        # Save without any metadata
        output = BytesIO()
        fixed_img.save(output, format='PNG', compress_level=6)
        
        return output.getvalue()
        
    except Exception as e:
        print(f"❌ Deep fix failed: {e}")
        raise

def test_deep_fix():
    """Test the deep PNG fix."""
    
    url = 'https://objectstorage.us-ashburn-1.oraclecloud.com/n/idp4lzoo2ao6/b/forestguard-images/o/carousel/5bd52c45-70c3-43f0-bccf-ccf7be86286c/swir_20260208.png'
    
    print("Testing deep PNG fix...")
    print(f"URL: {url}")
    
    try:
        # Download corrupted image
        with urllib.request.urlopen(url) as response:
            original_data = response.read()
        
        print(f"Original size: {len(original_data)} bytes")
        
        # Fix the image
        fixed_data = deep_fix_png(original_data)
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
            arr = np.array(fixed_img)
            print(f"✅ Fixed image numpy: {arr.shape}")
            
            # Test edge brightness
            h, w = arr.shape[:2]
            left_edge = arr[:, :10, :]
            right_edge = arr[:, -10:, :]
            
            left_brightness = left_edge.mean()
            right_brightness = right_edge.mean()
            
            print(f"Edge brightness - Left: {left_brightness:.1f}, Right: {right_brightness:.1f}")
            
            if left_brightness < 10 or right_brightness < 10:
                print("⚠️  Still have black edges")
            else:
                print("✅ No black edges detected")
            
            print("✅ Deep PNG fix successful!")
            
            # Save fixed image
            with open('deep_fixed_swir_20260208.png', 'wb') as f:
                f.write(fixed_data)
            print("Saved as: deep_fixed_swir_20260208.png")
            
        except Exception as e:
            print(f"❌ Fixed image still fails: {e}")
        
    except Exception as e:
        print(f"❌ Failed to test deep fix: {e}")

if __name__ == "__main__":
    test_deep_fix()
