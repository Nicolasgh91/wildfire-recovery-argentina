#!/usr/bin/env python3
"""
Test the watermark fix with actual corrupted image.
"""

import sys
import os
from pathlib import Path
from io import BytesIO
import urllib.request

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image
from app.utils.watermark import apply_watermark

def test_watermark_with_corrupted_image():
    """Test watermark processing with the actual corrupted image."""
    
    url = 'https://objectstorage.us-ashburn-1.oraclecloud.com/n/idp4lzoo2ao6/b/forestguard-images/o/carousel/5bd52c45-70c3-43f0-bccf-ccf7be86286c/swir_20260208.png'
    
    print("Testing watermark fix with corrupted image...")
    print(f"URL: {url}")
    
    try:
        # Download corrupted image
        with urllib.request.urlopen(url) as response:
            corrupted_data = response.read()
        
        print(f"Downloaded corrupted image: {len(corrupted_data)} bytes")
        
        # Test original corrupted image
        try:
            img = Image.open(BytesIO(corrupted_data))
            test_output = BytesIO()
            img.save(test_output, format='PNG')
            print("❌ Original image saves (unexpected!)")
        except Exception as e:
            print(f"✅ Original image fails as expected: {e}")
        
        # Test watermark with normal processing
        print("\nTesting watermark with corrupted input...")
        
        # Clear any feature flags
        os.environ.pop("DISABLE_WATERMARK_LOGO", None)
        os.environ.pop("DISABLE_WATERMARK_ALL", None)
        
        try:
            watermarked = apply_watermark(
                corrupted_data,
                acquisition_date="2026-02-08",
                label="Test"
            )
            
            print(f"✅ Watermark processing succeeded: {len(watermarked)} bytes")
            
            # Test the watermarked result
            try:
                result_img = Image.open(BytesIO(watermarked))
                print(f"✅ Watermarked image opens: {result_img.size} {result_img.mode}")
                
                # Test save
                test_output = BytesIO()
                result_img.save(test_output, format='PNG')
                print(f"✅ Watermarked image saves: {len(test_output.getvalue())} bytes")
                
                # Test numpy
                import numpy as np
                arr = np.array(result_img)
                print(f"✅ Watermarked image numpy: {arr.shape}")
                
                # Save for inspection
                with open('watermarked_fixed_swir_20260208.png', 'wb') as f:
                    f.write(watermarked)
                print("Saved as: watermarked_fixed_swir_20260208.png")
                
                print("✅ Watermark fix successful!")
                
            except Exception as e:
                print(f"❌ Watermarked result still corrupted: {e}")
        
        except Exception as e:
            print(f"❌ Watermark processing failed: {e}")
        
        # Test with logo disabled
        print("\nTesting with logo disabled...")
        os.environ["DISABLE_WATERMARK_LOGO"] = "true"
        
        try:
            watermarked_no_logo = apply_watermark(
                corrupted_data,
                acquisition_date="2026-02-08",
                label="Test"
            )
            
            print(f"✅ No-logo watermark: {len(watermarked_no_logo)} bytes")
            
            # Test result
            result_img = Image.open(BytesIO(watermarked_no_logo))
            test_output = BytesIO()
            result_img.save(test_output, format='PNG')
            print(f"✅ No-logo result saves: {len(test_output.getvalue())} bytes")
            
            with open('watermarked_no_logo_swir_20260208.png', 'wb') as f:
                f.write(watermarked_no_logo)
            print("Saved as: watermarked_no_logo_swir_20260208.png")
            
        except Exception as e:
            print(f"❌ No-logo watermark failed: {e}")
        
        # Clean up
        os.environ.pop("DISABLE_WATERMARK_LOGO", None)
        
    except Exception as e:
        print(f"❌ Failed to test: {e}")

if __name__ == "__main__":
    test_watermark_with_corrupted_image()
