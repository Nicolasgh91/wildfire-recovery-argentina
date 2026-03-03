# Watermark Debugging Guide

This guide helps diagnose and fix PNG corruption issues in carousel thumbnails by providing tools to disable watermark processing and test image integrity.

## Quick Commands for VM

Run these commands inside the VM where Docker containers are running:

### 1. Test PNG Integrity (No Numpy Required)
```bash
docker exec forestguard-api python -c "
import urllib.request
from PIL import Image
import io

url = 'https://objectstorage.us-ashburn-1.oraclecloud.com/n/idp4lzoo2ao6/b/forestguard-images/o/carousel/5bd52c45-70c3-43f0-bccf-ccf7be86286c/rgb_20260208.png'

try:
    with urllib.request.urlopen(url) as r:
        data = r.read()
    
    img = Image.open(io.BytesIO(data))
    w, h = img.size
    print(f'Dimensiones: {w}x{h}')
    print(f'Ratio: {w/h:.4f}')
    print(f'Tamaño: {len(data)/1024:.1f} KB')
    print(f'Modo: {img.mode}')
    
    # Test resave capability
    test_output = io.BytesIO()
    img.save(test_output, format='PNG')
    print('Resave test: OK')
    
    # Edge brightness test
    pixels = img.convert('RGB')
    left_edge = pixels.crop((0, 0, 10, h))
    right_edge = pixels.crop((w-10, 0, w, h))
    
    def get_brightness(area):
        colors = area.getcolors()
        if colors:
            total_pixels = sum(count for count, color in colors)
            total_brightness = sum(count * sum(color) for count, color in colors)
            return total_brightness / (total_pixels * 3)
        return 0
    
    left_b = get_brightness(left_edge)
    right_b = get_brightness(right_edge)
    print(f'Brillo izquierdo: {left_b:.1f}')
    print(f'Brillo derecho: {right_b:.1f}')
    
    if left_b < 10 or right_b < 10:
        print('⚠️ FRANJA NEGRA DETECTADA')
    else:
        print('✅ PNG parece OK')
        
except Exception as e:
    print(f'Error: {e}')
"
```

### 2. Test Multiple Images
```bash
docker exec forestguard-api python -c "
import urllib.request
from PIL import Image
import io

# Test different episode images
urls = [
    'https://objectstorage.us-ashburn-1.oraclecloud.com/n/idp4lzoo2ao6/b/forestguard-images/o/carousel/5bd52c45-70c3-43f0-bccf-ccf7be86286c/rgb_20260208.png',
    # Add more URLs from different episodes as needed
]

for i, url in enumerate(urls):
    try:
        with urllib.request.urlopen(url) as r:
            data = r.read()
        img = Image.open(io.BytesIO(data))
        print(f'Imagen {i+1}: {img.size} - OK')
    except Exception as e:
        print(f'Imagen {i+1}: ERROR - {e}')
"
```

## Feature Flag Implementation

### Environment Variables

Add these to your `.env` file or set them in the container:

```bash
# Disable watermark logo only (keeps date text)
DISABLE_WATERMARK_LOGO=true

# Disable all watermark processing (logo + text)
DISABLE_WATERMARK_ALL=true
```

### Usage Examples

#### 1. Disable Logo Only
```bash
# In docker-compose.yml or environment
environment:
  - DISABLE_WATERMARK_LOGO=true
```

#### 2. Disable All Watermark
```bash
# In docker-compose.yml or environment  
environment:
  - DISABLE_WATERMARK_ALL=true
```

## Diagnostic Scripts

### 1. PNG Corruption Diagnostic Tool
```bash
# Run inside container
docker exec forestguard-api python scripts/diagnose_png_corruption.py

# Test specific URL
docker exec forestguard-api python scripts/diagnose_png_corruption.py --url "https://..."

# Test watermark processing
docker exec forestguard-api python scripts/diagnose_png_corruption.py --test-watermark
```

### 2. Regenerate Single Episode
```bash
# Regenerate with normal watermark
docker exec forestguard-api python scripts/regenerate_episode_no_watermark.py EPISODE_ID

# Regenerate with logo disabled
docker exec forestguard-api python scripts/regenerate_episode_no_watermark.py EPISODE_ID --disable-logo

# Regenerate with all watermark disabled
docker exec forestguard-api python scripts/regenerate_episode_no_watermark.py EPISODE_ID --disable-all
```

## Testing Strategy

### Step 1: Diagnose Current Images
1. Run the PNG integrity test on existing images
2. Check for corruption warnings/errors
3. Verify aspect ratios are correct (4:3 = 1.3333)

### Step 2: Test Without Watermark
1. Set `DISABLE_WATERMARK_LOGO=true`
2. Regenerate a single episode
3. Test the new images for corruption
4. Compare with original images

### Step 3: Verify Fix
1. If watermark is the cause, images without watermark should be clean
2. Test frontend display with new images
3. Clear browser cache if needed

### Step 4: Production Deployment
1. Choose appropriate feature flag setting
2. Update environment variables
3. Regenerate affected episodes
4. Monitor for issues

## Expected Outcomes

### If Watermark Causes Corruption:
- Images with watermark: PIL errors, corruption warnings
- Images without watermark: Clean, no errors
- Solution: Keep watermark disabled or fix watermark processing

### If Watermark is NOT the Cause:
- Images with/without watermark: Both show corruption
- Solution: Issue is in GEE processing, storage, or elsewhere

## Troubleshooting

### Common Issues

1. **PIL Import Error**: Ensure Pillow is installed in container
2. **URL Access Error**: Check network connectivity and OCI permissions
3. **Environment Variables**: Verify flags are properly set in container
4. **Cache Issues**: Clear browser cache and CDN cache after regeneration

### Debug Steps

1. Check container logs for watermark processing
2. Verify environment variables are loaded
3. Test with different image URLs
4. Compare file sizes before/after watermark

## Implementation Details

### Feature Flag Logic

The watermark function checks these environment variables in order:

1. `DISABLE_WATERMARK_ALL` - If true, skips all watermark processing
2. `DISABLE_WATERMARK_LOGO` - If true, skips logo processing only
3. Normal processing - Applies both logo and text watermark

### File Changes Made

1. **app/utils/watermark.py**: Added feature flag checks
2. **.env.template**: Added watermark feature flag documentation
3. **scripts/diagnose_png_corruption.py**: Comprehensive diagnostic tool
4. **scripts/regenerate_episode_no_watermark.py**: Single episode regeneration tool

### Safety Features

- Graceful fallback if PIL is unavailable
- Logging for feature flag usage
- Environment cleanup after testing
- Error handling for all operations
