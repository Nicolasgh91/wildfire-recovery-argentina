# Branding Configuration

This project is designed to support white-labeling and easy rebranding. 
The branding configuration is centralized in two key files, one for the frontend and one for the backend.

## 1. Frontend Configuration

**File:** `frontend/src/config/brand.ts`

This file exports a `BRAND` constant containing:
- `name`: The application name displayed in the UI (e.g., "Vestigia").
- `tagline`: A short description.
- `logos`: Paths to light and dark mode logos.
- `assets`: Paths to favicons and social media images.

**To update the frontend branding:**
1. Open `frontend/src/config/brand.ts`.
2. Modify the values of `name`, `tagline`, or `logos`.
3. If changing logos, place the new image files in `frontend/public/assets/branding/` and update the paths in `brand.ts`.

## 2. Backend Configuration

**File:** `app/core/brand.py`

This python module defines a `BrandSettings` class with:
- `APP_NAME`: Used in PDF reports, email templates, and API titles.
- `APP_TAGLINE`: Used in descriptions.
- `APP_PUBLIC_URL`: Base URL for generating links.

**To update the backend branding:**
1. Open `app/core/brand.py`.
2. Modify `APP_NAME` or other constants.
3. Restart the backend service for changes to take effect.

## 3. Notes

- **Domain Name**: The domain name `forestguard.freedynamicdns.org` is currently preserved for infrastructure stability. Changing the domain requires updating SSL certificates, DNS records, and deployment scripts (`scripts/setup-ssl.sh`, etc.).
- **Database**: Internal database identifiers and some bucket names (`forestguard-images`) are kept as-is to avoid data migration complexity during this phase.
