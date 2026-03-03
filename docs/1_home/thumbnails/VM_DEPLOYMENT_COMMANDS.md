# VM Deployment Commands - PNG Corruption Fix

## 🚀 Deployment Commands for VM

### Step 1: Deploy the Code Changes
```bash
# Navigate to project directory
cd /path/to/wildfire-recovery-argentina

# Pull latest changes (if using git)
git pull origin main

# Restart the API service to apply changes
sudo systemctl restart forestguard-api
# OR if using docker-compose:
docker-compose restart api

# Verify service is running
sudo systemctl status forestguard-api
# OR:
docker-compose ps api
```

### Step 2: Test the Fix with Corrupted Image
```bash
# Test the watermark fix with the actual corrupted image
docker exec forestguard-api python scripts/test_watermark_fix.py

# Expected output should show:
# ✅ Watermark processing succeeded
# ✅ Watermarked image saves properly
# ✅ Numpy conversion works
```

### Step 3: Regenerate the Problematic Episode
```bash
# Regenerate the specific episode that had corruption issues
docker exec forestguard-api python scripts/regenerate_fixed_episode.py

# Expected output should show:
# ✅ Episode regenerated successfully!
# Generated X slides
# New slide URLs listed
```

### Step 4: Verify New Images
```bash
# Test the new images directly
docker exec forestguard-api python -c "
import urllib.request
from PIL import Image
import io
import numpy as np

# Test RGB image
url = 'https://objectstorage.us-ashburn-1.oraclecloud.com/n/idp4lzoo2ao6/b/forestguard-images/o/carousel/5bd52c45-70c3-43f0-bccf-ccf7be86286c/rgb_20260208.png'

print('Testing RGB image...')
with urllib.request.urlopen(url) as r:
    data = r.read()

img = Image.open(io.BytesIO(data))
print(f'✅ RGB opens: {img.size} {img.mode}')

# Test save
test_output = io.BytesIO()
img.save(test_output, format='PNG')
print(f'✅ RGB saves: {len(test_output.getvalue())} bytes')

# Test numpy
arr = np.array(img)
print(f'✅ RGB numpy: {arr.shape}')

# Test SWIR image
url_swir = 'https://objectstorage.us-ashburn-1.oraclecloud.com/n/idp4lzoo2ao6/b/forestguard-images/o/carousel/5bd52c45-70c3-43f0-bccf-ccf7be86286c/swir_20260208.png'

print('\nTesting SWIR image...')
with urllib.request.urlopen(url_swir) as r:
    data = r.read()

img_swir = Image.open(io.BytesIO(data))
print(f'✅ SWIR opens: {img_swir.size} {img_swir.mode}')

# Test save
test_output_swir = io.BytesIO()
img_swir.save(test_output_swir, format='PNG')
print(f'✅ SWIR saves: {len(test_output_swir.getvalue())} bytes')

# Test numpy
arr_swir = np.array(img_swir)
print(f'✅ SWIR numpy: {arr_swir.shape}')

print('\n🎉 All tests passed! PNG corruption fix is working.')
"
```

### Step 5: Test Frontend Display
```bash
# Check the frontend URL to verify images display correctly
curl -I "https://forestguard.freedynamicdns.org/fires/d3ed8298-697c-4ecb-8bcf-0f762296c403"

# Check image URLs are accessible
curl -I "https://objectstorage.us-ashburn-1.oraclecloud.com/n/idp4lzoo2ao6/b/forestguard-images/o/carousel/5bd52c45-70c3-43f0-bccf-ccf7be86286c/rgb_20260208.png"
curl -I "https://objectstorage.us-ashburn-1.oraclecloud.com/n/idp4lzoo2ao6/b/forestguard-images/o/carousel/5bd52c45-70c3-43f0-bccf-ccf7be86286c/swir_20260208.png"
```

### Step 6: Monitor Logs for Issues
```bash
# Monitor API logs for any watermark processing issues
docker exec forestguard-api tail -f /app/logs/app.log
# OR if using systemd:
sudo journalctl -u forestguard-api -f

# Look for these log messages:
# - "Input PNG appears corrupted, attempting reconstruction"
# - "Successfully reconstructed corrupted PNG"
# - "Watermark applied successfully"
```

### Step 7: Regenerate Additional Episodes (if needed)
```bash
# If you want to regenerate other episodes that might have corruption
# First get a list of recent episodes
docker exec forestguard-api python -c "
from app.db.session import SessionLocal
from app.services.imagery_service import ImageryService

db = SessionLocal()
service = ImageryService(db)

# Get recent episodes with slides
episodes = service._fetch_recent_episodes(limit=10)
for ep in episodes:
    if ep.slides_data:
        print(f'Episode {ep.id}: {len(ep.slides_data)} slides')

db.close()
"

# Regenerate specific episodes (replace with actual episode IDs)
docker exec forestguard-api python -c "
from app.db.session import SessionLocal
from app.services.imagery_service import ImageryService

db = SessionLocal()
service = ImageryService(db)

# Replace with actual episode IDs from the list above
episode_ids = [
    '5bd52c45-70c3-43f0-bccf-ccf7be86286c',  # The problematic one
    # Add more episode IDs here if needed
]

for ep_id in episode_ids:
    print(f'Regenerating episode {ep_id}...')
    result = service.refresh_episode(ep_id, force_refresh=True)
    print(f'Result: {result}')

db.close()
"
```

### Step 8: Emergency Rollback (if needed)
```bash
# If issues occur, disable watermarking completely
docker exec forestguard-api env DISABLE_WATERMARK_ALL=true python scripts/regenerate_fixed_episode.py

# Or set environment variable permanently
echo 'DISABLE_WATERMARK_ALL=true' >> .env
docker-compose restart api
```

## 🔍 Verification Checklist

After running the commands, verify:

- [ ] API service restarts successfully
- [ ] Test script shows "✅ Watermark processing succeeded"
- [ ] Episode regeneration completes without errors
- [ ] New images save and convert properly
- [ ] Frontend displays images without black bars
- [ ] No error messages in logs
- [ ] All image URLs return 200 OK

## 📞 Troubleshooting

If issues occur:
1. Check logs for error messages
2. Verify environment variables are set correctly
3. Use rollback commands to disable watermarking
4. Contact development team with log outputs

## ✅ Success Indicators

You'll know the fix is working when:
- All image processing completes successfully
- File sizes are reduced (from ~656KB to ~2-3KB)
- Frontend displays clean images without black bars
- No PIL/numpy conversion errors in logs
- New carousel thumbnails load properly
