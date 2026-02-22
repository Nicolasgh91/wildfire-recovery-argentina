# Branding Migration Report: ForestGuard -> Vestigia

## 1. References Finding
We scanned the codebase for "ForestGuard", "Wildfire Recovery", and "forestguard".

### Summary
- **"ForestGuard"**: ~113 occurences.
  - Hardcoded in UI components (`Navbar`, `Footer`, `Login`, `Register`).
  - Hardcoded in Scripts (`setup-ssl.sh`, `deploy.sh`, `celery_app.py`, writers in `scripts/`).
  - Hardcoded in Documentation (`README.md`, `docs/`).
  - Hardcoded in Docker/Nginx configs.
- **"Wildfire Recovery"**: ~1 occurence (in `deployment/forestguard.service`).
- **"forestguard"**: ~215 occurences.
  - Used in URLs/Domains (`forestguard.freedynamicdns.org`).
  - Used in S3/GCS Bucket names (`forestguard-images`, etc.).
  - Used in package names (`frontend/package.json`).
  - Used in file paths/service names.

### Detailed References (Sample)
*Full list analyzed internally.*

#### Frontend UI
- `frontend/src/components/layout/navbar.tsx`: `<span ...>ForestGuard</span>`
- `frontend/src/components/layout/footer.tsx`: Copyright, Links.
- `frontend/src/pages/Login.tsx`, `Register.tsx`: Titles.
- `frontend/index.html`: `<title>ForestGuard...</title>`

#### Backend & Scripts
- `app/core/config.py` (checked via grep): Likely contains project name.
- `scripts/setup-ssl.sh`, `renew-ssl.sh`: echo "ForestGuard..."
- `workers/__init__.py`: "ForestGuard Workers Package"

#### Infrastructure / DevOps
- `nginx.conf`: `server_name forestguard.freedynamicdns.org;`
- `docker-compose.yml`: container names or labels (to be verified).
- `README.md`: Title and descriptions.

## 2. Plan for "Single Source of Truth"

### Frontend (`frontend/src/config/brand.ts`)
```typescript
export const BRAND = {
  name: "Vestigia", // Was ForestGuard
  tagline: "Wildfire Recovery & Monitoring",
  logos: {
    light: "/assets/branding/logo-light.svg", // TBD
    dark: "/assets/branding/logo-dark.svg",   // TBD
  },
  favicon: "/favicon.ico",
  meta: {
    ogImage: "/assets/branding/og-image.jpg",
  }
};
```

### Backend (`app/core/brand.py`)
```python
class BrandSettings:
    APP_NAME = "Vestigia"
    APP_TAGLINE = "Wildfire Recovery & Monitoring"
    APP_PUBLIC_URL = "https://forestguard.freedynamicdns.org" # Keeping domain for now
    APP_BRAND_SLUG = "vestigia"

brand = BrandSettings()
```

## 3. Implementation Checklist (Phase 1)
- [ ] Create config files.
- [ ] Refactor Frontend components to import `BRAND`.
- [ ] Refactor Backend templates/reports to import `brand`.
- [ ] Update `README.md` (carefully, matching new brand but keeping repo context).

## 4. Risks & Reversion
- **Risk**: Breaking assets links if we move logo files without redirects or updates.
- **Risk**: SSL transparency logs will still show old domain (acceptable).
- **Mitigation**: We will NOT change the domain `forestguard.freedynamicdns.org` or bucket names in this phase.
- **Reversion**: Revert commits; the config files allow quick toggling back to "ForestGuard" by changing string values.

## 5. Verification Results (Phase 1)

### Status: COMPLETED WITH WARNINGS

#### Implemented Changes
- Created `frontend/src/config/brand.ts` and `app/core/brand.py`.
- Updated `Navbar`, `Footer`, `Login`, `Register`, `index.html`.
- Updated `app/core/config.py`, `scripts/setup-ssl.sh`, `README.md`, `app/main.py`, `deployment/forestguard.service`.
- Centralized naming to "Vestigia".

#### Verification Findings
- **Frontend Build**: Fails with 49 pre-existing TypeScript errors (unrelated to branding).
  - *Action*: Fixed `vite.config.ts` type errors to progress build.
  - *Note*: `BRAND` imports are valid and causing no errors.
- **Backend Tests**: `pytest` found no tests (empty `tests/` directories).
- **Manual Check**: References to "ForestGuard" replaced in target files.
  - `forestguard.freedynamicdns.org` preserved as requested.
  - `forestguard` service/container names preserved as requested.

#### Recommendations for Phase 2
- [ ] Fix pre-existing 49 TypeScript errors in frontend to enable clean builds.
- [ ] Populate backend tests.
- [ ] Create proper logo assets for `frontend/public/assets/branding/`.
- [ ] Schedule full domain migration (renaming `forestguard.freedynamicdns.org`).
