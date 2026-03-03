> **Nota (2026-03)**  
> Esta copia se mantiene solo por compatibilidad histórica.  
> El archivo vivo y referenciado desde el índice se encuentra en:  
> `docs/1_home/thumbnails/PNG_CORRUPTION_FIX_SUMMARY.md`.  
> Para operación diaria usar además los docs bajo `docs/core-flows/core-preproceso-imagenes/`.

# PNG Corruption Fix - IMPLEMENTATION COMPLETE

## 🎯 Problem Identified

The PNG corruption issue was **NOT** caused by the watermark processing itself, but by **corrupted PNG metadata** in the input images from GEE/storage. The corruption prevented PIL from performing basic operations like `save()` and `numpy.array()` conversion.

## 🔍 Root Cause Analysis

### Issue Pattern
- **Input PNGs**: Open fine but fail on save/numpy conversion
- **Error**: `argument 2 must be 4-item tuple, not str`
- **Source**: Corrupted PNG metadata (tEXt chunks) from GEE/storage pipeline
- **Impact**: All carousel thumbnails with watermark metadata

### Diagnostic Results
```
✅ PIL open: (768, 576) RGBA
❌ Save test failed: argument 2 must be 4-item tuple, not str
❌ Numpy conversion failed: same error
```

## 🛠️ Solution Implemented

### 1. PNG Corruption Detection & Recovery
- **File**: `app/utils/watermark.py`
- **Function**: `_fix_corrupted_png()`
- **Method**: Pixel-by-pixel reconstruction using numpy arrays
- **Fallback**: Graceful degradation if reconstruction fails

### 2. Integration Points
- **Watermark Processing**: Detects and fixes corrupted input before processing
- **Validation**: Post-watermark validation to ensure clean output
- **Feature Flags**: Maintained for debugging (`DISABLE_WATERMARK_LOGO`, `DISABLE_WATERMARK_ALL`)

### 3. Key Improvements
- **Redundant convert() removed**: Fixed `combined.convert("RGBA").save()` issue
- **Metadata handling**: Safe PNG metadata creation with error handling
- **Compression**: Added `compress_level=6` for consistent output
- **Validation**: Built-in corruption detection and recovery

## 🧪 Testing Results

### Before Fix
```
❌ Original image fails: argument 2 must be 4-item tuple, not str
❌ All save operations fail
❌ Numpy conversion fails
```

### After Fix
```
✅ Watermark processing succeeded: 2252 bytes
✅ Watermarked image opens: (768, 576) RGBA
✅ Watermarked image saves: 2252 bytes
✅ Watermarked image numpy: (576, 768, 4)
✅ No black edges detected
```

## 📁 Files Modified

### Core Implementation
- **`app/utils/watermark.py`**: Added corruption detection and recovery
- **`scripts/diagnose_pipeline_corruption.py`**: Comprehensive pipeline diagnostic
- **`scripts/test_watermark_fix.py`**: Validation with real corrupted images

### Diagnostic Tools
- **`scripts/analyze_corruption_pattern.py`**: Deep corruption analysis
- **`scripts/deep_png_fix.py`**: Standalone PNG reconstruction
- **`scripts/regenerate_fixed_episode.py`**: Episode regeneration with fix

## 🚀 Ready for Production

### VM Commands
```bash
# Regenerate the problematic episode
docker exec forestguard-api python scripts/regenerate_fixed_episode.py

# Test the new images
docker exec forestguard-api python -c "
import urllib.request
from PIL import Image
import io

url = 'https://objectstorage.us-ashburn-1.oraclecloud.com/n/idp4lzoo2ao6/b/forestguard-images/o/carousel/5bd52c45-70c3-43f0-bccf-ccf7be86286c/rgb_20260208.png'

with urllib.request.urlopen(url) as r:
    data = r.read()

img = Image.open(io.BytesIO(data))
print(f'✅ Fixed image: {img.size} {img.mode}')

# Test numpy
import numpy as np
arr = np.array(img)
print(f'✅ Numpy conversion: {arr.shape}')
"
```

### Expected Outcome
- **Clean PNG files** that save and convert properly
- **No black bars** in frontend display
- **Proper numpy conversion** for any processing
- **Maintained image quality** with smaller file sizes

## 🔄 Rollback Plan

If issues occur:
1. Set `DISABLE_WATERMARK_ALL=true` to disable watermarking completely
2. Regenerate affected episodes
3. Monitor for any remaining corruption

## ✅ Implementation Status: COMPLETE

The PNG corruption issue has been **fully resolved** with:
- ✅ Root cause identified (corrupted PNG metadata)
- ✅ Robust fix implemented (pixel reconstruction)
- ✅ Comprehensive testing completed
- ✅ Production-ready deployment tools
- ✅ Rollback procedures documented

The fix will automatically detect and reconstruct corrupted PNGs during watermark processing, ensuring all future carousel thumbnails are clean and properly formatted.
