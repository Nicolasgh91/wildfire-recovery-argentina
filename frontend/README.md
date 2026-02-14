# ForestGuard Frontend

React + Vite + Tailwind UI for ForestGuard.

## Architecture overview

### Entry points
- `index.html` is the Vite HTML shell.
- `src/main.tsx` mounts React, pulls global styles, and registers the toast system.
- `src/App.tsx` wires providers (theme, i18n, auth) and the router.

### Routing
`react-router-dom` handles all routes inside `App.tsx`.

Key routes:
- `/` -> Home
- `/map` -> Map
- `/audit` -> Verificar terreno (requiere login)
- `/exploracion` -> Exploración satelital (wizard)
- `/reports` -> Redirección a `/exploracion` (compatibilidad legacy)
- `/credits` -> Credits purchase and balance
- `/certificates` -> Certificates (feature flag `certificates`)
- `/citizen-report` -> Citizen reports
- `/fires/history` -> Fire history (server-side pagination, requiere login)
- `/fires/:id` -> Fire detail
- `/shelters` -> Shelters + visitor logs (feature flag `refuges`)
- `/faq`, `/manual`, `/glossary`, `/contact`

### State and data flow
- Local component state for pages, plus React Query for server state.
- `AuthContext` integrates Supabase Auth with role mapping.
- `LanguageContext` provides a basic i18n dictionary from `src/data/translations.ts`.
- Centralized API client in `src/services/api.ts` with module endpoints in `src/services/endpoints`.

### API integration
- Default API base is `/api/v1` (Vite dev proxy forwards `/api` to `http://localhost:8000`).
- Optional override via `VITE_API_BASE_URL` for full URLs.
- Data fetching uses `src/services` endpoints + React Query hooks; some pages still use mock data until backend wiring.

### Architecture diagram (ASCII)
```
Browser
  |
  v
React App (Vite)
  |-- Providers (Theme, I18n, Auth)
  |-- Router (react-router)
  |-- Pages
  |     |-- FireHistory -> /api/v1/fires, /api/v1/fires/stats, /api/v1/fires/export
  |     |-- Shelters    -> /api/v1/shelters, /api/v1/visitor-logs
  |     |-- Contact     -> /api/v1/contact
  |     |-- Other pages -> mockdata (local)
  |-- UI (shadcn/ui + Tailwind)
  |-- Maps (Leaflet) / Charts (Recharts)
  v
API (FastAPI, /api/v1)
```

### API contracts per page
- `/` Home: no API calls.
- `/map`: uses mock data (`src/data/mockdata.ts`). Planned: `GET /api/v1/fires` with `status_scope=active`.
- `/audit` (live):
  - `POST /api/v1/audit/land-use`
    - Body: `{ lat, lon, radius_meters, cadastral_id? }`
    - Response: `AuditResponse` (see backend `app/api/v1/audit.py`)
- `/exploracion` (live):
  - `POST /api/v1/explorations/`
  - `GET /api/v1/explorations/`
  - `GET /api/v1/explorations/{id}`
  - `PATCH /api/v1/explorations/{id}`
  - `POST /api/v1/explorations/{id}/items`
  - `DELETE /api/v1/explorations/{id}/items/{item_id}`
  - `POST /api/v1/explorations/{id}/quote`
  - `POST /api/v1/explorations/{id}/generate`
  - `GET /api/v1/explorations/{id}/assets`
- `/reports` (legacy alias):
  - Frontend redirige a `/exploracion` para compatibilidad de enlaces.
- `/reports` (live API helpers):
  - `POST /api/v1/reports/judicial`
    - Body: `{ fire_event_id, report_type?, include_climate?, include_imagery?, requester_name?, case_reference?, language? }`
    - Response: `JudicialReportResponse` (`src/types/report.ts`)
  - `POST /api/v1/reports/historical`
    - Body: `{ protected_area_id?, protected_area_name?, start_date, end_date, include_monthly_images?, max_images?, language? }`
    - Response: `HistoricalReportResponse` (`src/types/report.ts`)
  - Credits balance endpoint pending (UI uses fallback if unavailable).
- `/payments` (live):
  - `POST /api/v1/payments/checkout`
  - `GET /api/v1/payments/pricing` (ARS prices + exchange rate)
  - `GET /api/v1/payments/{payment_request_id}`
  - `GET /api/v1/payments/credits/balance`
  - `GET /api/v1/payments/credits/transactions`
- `/certificates`: usa mock data y está detrás de `feature flag` (`certificates`). Planned:
  - `POST /api/v1/certificates/issue`
    - Body: `{ fire_event_id, issued_to, requester_email }`
    - Response: `{ status, certificate_number, download_url, verification_hash }`
  - `GET /api/v1/certificates/verify/{certificate_number}`
    - Response: `{ status, message, data? }`
  - `GET /api/v1/certificates/download/{certificate_number}` -> PDF stream
- `/citizen-report`: uses mock data. Planned:
  - `POST /api/v1/citizen/submit`
    - Body: `{ latitude, longitude, report_type, description, observed_date?, reporter_email?, reporter_name? }`
    - Response: `CitizenReportResponse`
  - `GET /api/v1/citizen/status/{report_id}`
  - `GET /api/v1/citizen/{report_id}/evidence`
- `/fires/history` (live):
  - `GET /api/v1/fires`
    - Query: `status_scope`, `province`, `date_from`, `date_to`, `search`, `sort_by`, `sort_desc`, `page`, `page_size`
    - Response: `FireListResponse` (`src/types/fire.ts`)
    - Note: on mobile, `page_size` is clamped to max 50.
  - `GET /api/v1/fires/stats`
    - Query: `province`, `date_from`, `date_to`
    - Response: `FireStatsResponse` (`src/types/fire.ts`)
  - `GET /api/v1/fires/export`
    - Query: same filters + `format=csv`
    - Response: CSV download
- `/fires/:id`: uses mock data. Planned:
  - `GET /api/v1/fires/{id}` -> `FireDetailResponse`
  - `POST /api/v1/reports/judicial` -> report metadata/download URLs
- `/shelters` (live):
  - `GET /api/v1/shelters?province=&query=`
    - Response: `{ shelters: [{ id, name, province, location_description, carrying_capacity, is_active }], total }`
  - `POST /api/v1/visitor-logs`
    - Body: `{ shelter_id, visit_date, registration_type, group_leader_name, contact_email?, contact_phone?, companions[] }`
    - Response: `VisitorLogResponse`
  - Offline queue stored in `localStorage` key `visitorLogQueue` and synced when online.
- `/contact` (live):
  - `POST /api/v1/contact` (multipart/form-data)
    - Fields: `name`, `email`, `subject`, `message`, optional `attachment`
    - Response: `ContactResponse` (`src/types/contact.ts`)
- `/faq`, `/manual`, `/glossary`, `/login`, `/not-found`: no API calls.

### UI system
- Tailwind CSS for styling; shared utility `cn()` in `src/lib/utils.ts`.
- shadcn/ui components live in `src/components/ui` (Radix primitives + Tailwind).
- Layout chrome in `src/components/layout` (navbar + footer).
- Feature UI in `src/components/fires` (filters, pagination, cards).

### Maps and charts
- Leaflet + react-leaflet for map views.
- Optional H3 heatmap rendering via leaflet.glify (WebGL).
- Map composition lives in `src/components/map` (BaseMap, MapView, layers).
- Recharts for charts on the fire history dashboard.

### Tests
- Vitest + Testing Library; setup in `src/test/setup.ts`.
- Cypress E2E in `cypress/e2e` (baseUrl in `cypress.config.ts`).

## Folder structure (high level)
- `src/pages`: Route-level screens.
- `src/components`: Shared components and feature UI.
- `src/components/ui`: shadcn/ui primitives.
- `src/context`: Auth + i18n providers.
- `src/types`: Shared domain types (fire data, pagination, stats).
- `src/hooks`: Small utilities (ex: `use-mobile`).
- `src/data`: Static data and translation dictionaries.
- `src/assets`: Static images.
- `public`: Public assets served by Vite.

## Audit notes (current state)
- Centralized API client with axios + interceptors in `src/services/api.ts`.
- Auth integrates Supabase; JWT injection is controlled by `VITE_USE_SUPABASE_JWT`.
- API calls rely on the Vite proxy in dev and `VITE_API_BASE_URL` in other envs.
- Optional error tracking uses `VITE_SENTRY_DSN` (leave empty to disable).

## Requirements
- Node 18+ (for fetch in scripts)
- Backend running locally or a remote API URL

## Setup
1. From `frontend/`, install deps: `npm install`
2. Copy `.env.example` to `.env` and set `VITE_API_BASE_URL`
3. Start the backend (from repo root):
   - `uvicorn app.main:app --reload --port 8000`
   - or `docker-compose up -d`

## Run the frontend
`npm run dev`

## Backend health check
`npm run backend:health`

## Tests
`npm run test -- --run`

## Notas recientes
- La tarjeta de "Calidad de datos" en FireDetail est� comentada temporalmente; el resto de las tarjetas se reacomoda autom�ticamente.
- El carrusel "Obtener im�genes HD" est� oculto temporalmente; las tarjetas restantes ocupan su espacio.
## Notas recientes
- La tarjeta de 'Calidad de datos' en FireDetail está comentada temporalmente; el resto de las tarjetas se reacomoda automáticamente.
- El carrusel 'Obtener imágenes HD' está oculto temporalmente; las tarjetas restantes ocupan su espacio.
- Los íconos/imports de secciones ocultas (ej. Download, AlertTriangle, Flame, MapPin) se mantienen para reactivarlos rápido.

