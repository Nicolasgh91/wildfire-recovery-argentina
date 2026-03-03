#!/usr/bin/env python3
"""
Test the current corrupted image to understand the corruption pattern.
"""

import sys
from pathlib import Path
from io import BytesIO
import urllib.request

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image

def test_current_image():
    """Test the current corrupted image from storage."""
    
    url = 'https://objectstorage.us-ashburn-1.oraclecloud.com/n/idp4lzoo2ao6/b/forestguard-images/o/carousel/5bd52c45-70c3-43f0-bccf-ccf7be86286c/swir_20260208.png'
    
    print("Testing current corrupted image...")
    print(f"URL: {url}")
    
    try:
        with urllib.request.urlopen(url) as response:
            data = response.read()
        
        print(f"Downloaded: {len(data)} bytes")
        
        # Test basic PIL opening
        img = Image.open(BytesIO(data))
        print(f"✅ PIL open: {img.size} {img.mode}")
        
        # Test save
        try:
            output = BytesIO()
            img.save(output, format='PNG')
            print(f"✅ Save test: {len(output.getvalue())} bytes")
        except Exception as e:
            print(f"❌ Save test failed: {e}")
            return
        
        # Test numpy conversion
        try:
            import numpy as np
            arr = np.array(img)
            print(f"✅ Numpy test: {arr.shape}")
        except Exception as e:
            print(f"❌ Numpy test failed: {e}")
            print("This is the corruption we need to fix!")
            
            # Try to understand the error
            if "argument 2 must be sequence of length 4" in str(e):
                print("🔍 Error suggests RGBA channel issue")
            
            return
        
        # Test individual channels
        print("Testing individual channels...")
        try:
            if img.mode == 'RGBA':
                r, g, b, a = img.split()
                print(f"✅ Channels split: R={r.size}, G={g.size}, B={b.size}, A={a.size}")
                
                # Test recombining
                combined = Image.merge('RGBA', (r, g, b, a))
                print("✅ Channels recombine: OK")
            else:
                print(f"Image mode: {img.mode}")
        except Exception as e:
            print(f"❌ Channel test failed: {e}")
        
        # Test converting to RGB then back
        try:
            rgb = img.convert('RGB')
            print(f"✅ RGB conversion: {rgb.size}")
            
            rgba_back = rgb.convert('RGBA')
            print(f"✅ RGBA back conversion: {rgba_back.size}")
            
            # Test numpy on converted
            arr_rgb = np.array(rgb)
            print(f"✅ Numpy on RGB: {arr_rgb.shape}")
            
        except Exception as e:
            print(f"❌ Conversion test failed: {e}")
        
    except Exception as e:
        print(f"❌ Failed to download/open image: {e}")

if __name__ == "__main__":
    test_current_image()
