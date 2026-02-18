# Auth Validation Runbook (ForestGuard)

Date: 2026-02-12
Scope: Supabase Auth + Audit + Mercado Pago + Android (Capacitor)

## Required env vars
Frontend:
- VITE_SUPABASE_URL
- VITE_SUPABASE_ANON_KEY
- VITE_API_BASE_URL
- VITE_USE_SUPABASE_JWT=true
- (Optional) VITE_AUTH_REDIRECT_URL
- (Optional) VITE_CLIENT_PLATFORM=web|android

Backend:
- SUPABASE_URL
- SUPABASE_JWT_SECRET
- SUPABASE_JWT_AUDIENCE=authenticated
- PAYMENT_SUCCESS_URL / PAYMENT_FAILURE_URL / PAYMENT_PENDING_URL
- (Optional) PAYMENT_*_URL_ANDROID for deep links

## Local commands
- Frontend: `npm run dev`
- Backend: `uvicorn app.main:app --reload --port 8000`

## Manual validation checklist
1) Email/password login
- Go to /login, sign in.
- Verify navbar shows profile and ProtectedRoute pages render.

2) Google OAuth login
- Click "Login con Google".
- Ensure redirect returns to /auth/callback and then to the original page.

3) Audit flow
- Open /audit.
- Run an audit; confirm request succeeds with JWT only (no API key required).

4) Payments (Mercado Pago)
- Open /credits or /profile.
- Start checkout and complete payment (or mock mode).
- Return to /payments/return and verify status resolves.

5) Session persistence
- Refresh the page; verify AuthContext restores session and API calls still include Authorization.

6) Logout
- Sign out and verify protected routes redirect to /login.

## Android (Capacitor) notes
- Configure deep links:
  - forestguard://auth/callback
  - forestguard://payments/return
- Ensure Supabase allowed redirect URLs include the scheme above.
- Set VITE_CLIENT_PLATFORM=android and VITE_AUTH_REDIRECT_URL=forestguard://auth/callback for Android builds.
- Set PAYMENT_*_URL_ANDROID in backend to forestguard://payments/return?status=...

## Expected outcomes
- No native auth endpoints accessible (/api/v1/auth/* removed).
- All user-protected endpoints accept Supabase JWT only.
- Payment return works after external redirects without losing session.

