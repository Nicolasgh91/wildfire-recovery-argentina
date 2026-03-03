#!/usr/bin/env python3
"""
Analyze the specific corruption pattern in the current images.
"""

import sys
from pathlib import Path
from io import BytesIO
import urllib.request

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image, PngImagePlugin

def analyze_corruption():
    """Analyze the corruption pattern in detail."""
    
    url = 'https://objectstorage.us-ashburn-1.oraclecloud.com/n/idp4lzoo2ao6/b/forestguard-images/o/carousel/5bd52c45-70c3-43f0-bccf-ccf7be86286c/swir_20260208.png'
    
    print("Analyzing corruption pattern...")
    print(f"URL: {url}")
    
    try:
        with urllib.request.urlopen(url) as response:
            data = response.read()
        
        print(f"Downloaded: {len(data)} bytes")
        
        # Test basic PIL opening
        img = Image.open(BytesIO(data))
        print(f"✅ PIL open: {img.size} {img.mode}")
        
        # Check image info
        print(f"Format: {img.format}")
        print(f"Info keys: {list(img.info.keys())}")
        
        # Check if PNG info exists
        if hasattr(img, 'pnginfo'):
            print(f"PNG info: {img.pnginfo}")
        
        # Test different save methods
        print("\nTesting different save methods:")
        
        # Method 1: Basic save
        try:
            output1 = BytesIO()
            img.save(output1, format='PNG')
            print(f"✅ Basic save: {len(output1.getvalue())} bytes")
        except Exception as e:
            print(f"❌ Basic save failed: {e}")
        
        # Method 2: Save without parameters
        try:
            output2 = BytesIO()
            img.save(output2, 'PNG')
            print(f"✅ Save without params: {len(output2.getvalue())} bytes")
        except Exception as e:
            print(f"❌ Save without params failed: {e}")
        
        # Method 3: Save with compress_level
        try:
            output3 = BytesIO()
            img.save(output3, format='PNG', compress_level=6)
            print(f"✅ Save with compress_level: {len(output3.getvalue())} bytes")
        except Exception as e:
            print(f"❌ Save with compress_level failed: {e}")
        
        # Method 4: Convert to RGB first
        try:
            rgb_img = img.convert('RGB')
            output4 = BytesIO()
            rgb_img.save(output4, format='PNG')
            print(f"✅ RGB conversion + save: {len(output4.getvalue())} bytes")
        except Exception as e:
            print(f"❌ RGB conversion + save failed: {e}")
        
        # Method 5: Create new image and copy pixels
        try:
            new_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
            new_img.paste(img, (0, 0))
            output5 = BytesIO()
            new_img.save(output5, format='PNG')
            print(f"✅ New image + copy: {len(output5.getvalue())} bytes")
        except Exception as e:
            print(f"❌ New image + copy failed: {e}")
        
        # Test numpy conversion
        print("\nTesting numpy conversion:")
        try:
            import numpy as np
            arr = np.array(img)
            print(f"✅ Numpy conversion: {arr.shape}")
            
            # Convert back to image
            img_from_array = Image.fromarray(arr)
            output6 = BytesIO()
            img_from_array.save(output6, format='PNG')
            print(f"✅ Array -> Image -> Save: {len(output6.getvalue())} bytes")
            
        except Exception as e:
            print(f"❌ Numpy conversion failed: {e}")
        
        # Check PNG chunks
        print("\nAnalyzing PNG structure:")
        try:
            # Read PNG chunks manually
            png_data = BytesIO(data)
            png_data.read(8)  # Skip signature
            
            chunks = []
            while True:
                chunk_data = png_data.read(4)
                if not chunk_data:
                    break
                
                chunk_len = int.from_bytes(chunk_data, byteorder='big')
                chunk_type = png_data.read(4)
                chunk_content = png_data.read(chunk_len)
                chunk_crc = png_data.read(4)
                
                chunks.append({
                    'type': chunk_type.decode('ascii'),
                    'length': chunk_len,
                    'crc': chunk_crc.hex()
                })
                
                if chunk_type == b'IEND':
                    break
            
            print(f"Found {len(chunks)} chunks:")
            for chunk in chunks:
                print(f"  {chunk['type']}: {chunk['length']} bytes")
                
        except Exception as e:
            print(f"❌ PNG chunk analysis failed: {e}")
        
    except Exception as e:
        print(f"❌ Failed to analyze image: {e}")

if __name__ == "__main__":
    analyze_corruption()
