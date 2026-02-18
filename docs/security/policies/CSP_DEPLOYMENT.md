# Content Security Policy (CSP) Deployment Guide

## Overview

Content Security Policy (CSP) is implemented in Nginx to protect against XSS and other injection attacks. The policy is currently in **Report-Only Mode** to monitor violations before enforcement.

## Current Status

**Mode**: `Content-Security-Policy-Report-Only`  
**Location**: `deployment/nginx.conf`  
**Enforcement**: Not yet enforced (monitoring phase)

## CSP Policy Details

```
default-src 'self';
script-src 'self' 'unsafe-inline' 'unsafe-eval' https://maps.googleapis.com https://www.googletagmanager.com;
style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
img-src 'self' data: https: blob:;
font-src 'self' https://fonts.gstatic.com;
connect-src 'self' https://*.supabase.co https://*.supabase.in wss://*.supabase.co https://api.mercadopago.com https://storage.googleapis.com;
frame-src 'none';
frame-ancestors 'none';
object-src 'none';
base-uri 'self';
form-action 'self' https://www.mercadopago.com;
```

## Deployment Phases

### Phase 1: Report-Only Mode (Current - 48 hours minimum)

**Goal**: Monitor CSP violations without blocking any content.

**Actions**:
1. ✅ CSP header added to Nginx in report-only mode
2. ⏳ Monitor browser console for CSP violations
3. ⏳ Check application functionality (48h minimum)
4. ⏳ Adjust policy based on violations

**How to Monitor**:
- Open browser DevTools (F12)
- Go to Console tab
- Look for messages starting with "Content Security Policy"
- Document any blocked resources

### Phase 2: Policy Refinement (After 48h)

**Goal**: Adjust policy based on real violations.

**Common Adjustments Needed**:
- Add missing domains to `connect-src`
- Add inline script hashes instead of `'unsafe-inline'`
- Add specific Google Analytics domains if used
- Add CDN domains for third-party libraries

**How to Refine**:
1. Collect all violation reports from Phase 1
2. Identify legitimate resources being blocked
3. Update policy in `deployment/nginx.conf`
4. Reload Nginx: `sudo nginx -s reload`
5. Monitor for another 24-48h

### Phase 3: Enforcement (After successful refinement)

**Goal**: Enable CSP enforcement to block violations.

**Actions**:
1. Change header from `Content-Security-Policy-Report-Only` to `Content-Security-Policy`
2. Update Nginx config:
   ```nginx
   add_header Content-Security-Policy "..." always;
   ```
3. Reload Nginx
4. Monitor closely for 24h
5. Have rollback plan ready

## Known Limitations

### ⚠️ 'unsafe-inline' and 'unsafe-eval'

The current policy includes `'unsafe-inline'` and `'unsafe-eval'` in `script-src`, which **reduces CSP effectiveness** against XSS.

**Why included**:
- React/Vite may use inline scripts during development
- Some third-party libraries require eval

**Future improvement**:
- Use script nonces or hashes instead of `'unsafe-inline'`
- Migrate away from libraries requiring `'unsafe-eval'`
- Generate CSP hashes during build: `npm run build` should output hashes

**How to remove 'unsafe-inline'**:
1. Build production bundle: `npm run build`
2. Collect script hashes from build output
3. Replace `'unsafe-inline'` with `'sha256-HASH1' 'sha256-HASH2'`
4. Test thoroughly

## Testing Checklist

Before moving to enforcement, verify:

- [ ] Frontend loads without errors
- [ ] User authentication works (Supabase)
- [ ] Google OAuth login works
- [ ] MercadoPago payment flow works
- [ ] Google Maps displays correctly
- [ ] File uploads work
- [ ] API calls succeed
- [ ] WebSocket connections work (if applicable)
- [ ] No CSP violations in console (48h monitoring)

## Rollback Plan

If CSP causes issues in production:

1. **Immediate rollback** (< 1 minute):
   ```bash
   # Remove CSP header from nginx.conf
   sudo nano /etc/nginx/sites-available/forestguard
   # Comment out the add_header Content-Security-Policy line
   sudo nginx -t
   sudo nginx -s reload
   ```

2. **Revert to report-only**:
   ```bash
   # Change Content-Security-Policy to Content-Security-Policy-Report-Only
   sudo nginx -s reload
   ```

## Monitoring Commands

```bash
# Check Nginx config syntax
sudo nginx -t

# Reload Nginx (graceful)
sudo nginx -s reload

# View Nginx error log
sudo tail -f /var/log/nginx/forestguard_error.log

# View Nginx access log
sudo tail -f /var/log/nginx/forestguard_access.log
```

## Additional Resources

- [MDN CSP Guide](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
- [CSP Evaluator](https://csp-evaluator.withgoogle.com/)
- [Report URI](https://report-uri.com/) - CSP reporting service

## Next Steps

1. Deploy updated `nginx.conf` to production
2. Monitor for 48 hours minimum
3. Document any violations
4. Refine policy based on violations
5. Remove `'unsafe-inline'` if possible
6. Move to enforcement mode
