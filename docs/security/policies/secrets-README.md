# Secrets Directory

This directory contains sensitive credentials that should **NEVER** be committed to git.

## Contents

- `gee-service-account.json` - Google Earth Engine service account credentials

## Security Notes

⚠️ **CRITICAL**: This entire directory is ignored by `.gitignore`

✅ Files in this directory are safe from accidental commits  
✅ Add any other credentials here (API keys, tokens, etc.)  
❌ Never share these files publicly or via email

## Setup

When deploying to production:

1. Copy credentials to this directory
2. Update `.env` to reference `./secrets/[filename]`
3. Ensure `.gitignore` includes `secrets/`

## Production

For production environments (Oracle Cloud, AWS, etc.):
- Use environment variables instead of files when possible
- Store files in `/opt/secrets/` or similar secure location
- Set restrictive permissions: `chmod 600 secrets/*`
