# FE-GA-01: Login Google Auth (Supabase OAuth)

**Fecha**: 2026-02-05  
**Owner**: Frontend  
**Estado**: Pendiente

## Objetivo
Habilitar login con Google via Supabase OAuth y exponer el flujo en la UI del login, manteniendo consistencia con el design system actual.

## Alcance
- Frontend: boton "Continuar con Google" + manejo de errores/estado.
- Supabase: configuracion del provider Google.
- Google Cloud: credenciales OAuth y URIs autorizadas.
- No incluye cambios en backend (ya consume JWT de Supabase).

## Requisitos / Inputs
- Supabase project creado.
- Dominio de produccion definido (ej: https://forestguard.ar).
- Acceso a Google Cloud Console (crear OAuth Client).
- Variables de entorno:
  - `VITE_SUPABASE_URL`
  - `VITE_SUPABASE_ANON_KEY`
  - `VITE_USE_SUPABASE_JWT=true`

## Paso a paso (configuracion)

### 1) Google Cloud Console
1. Crear proyecto (o usar uno existente).
2. Configurar OAuth Consent Screen (External).
3. Crear credenciales OAuth 2.0 Client ID (Web application).
4. Agregar **Authorized redirect URIs**:
   - `https://<project-ref>.supabase.co/auth/v1/callback`
5. Agregar **Authorized JavaScript origins**:
   - `http://localhost:5173`
   - `https://forestguard.freedynamicdns.org/` (o el dominio real)

> Nota: el redirect URI **siempre** es el callback de Supabase.

### 2) Supabase Dashboard
1. Authentication → Providers → Google.
2. Pegar **Client ID** y **Client Secret** de Google.
3. Authentication → URL Configuration:
   - Site URL: `https://forestguard.freedynamicdns.org/`
   - Additional Redirect URLs:
     - `http://localhost:5173`
     - `https://forestguard.freedynamicdns.org/`

### 3) Frontend (AuthContext)
Agregar metodo `signInWithGoogle` usando `supabase.auth.signInWithOAuth`.

```ts
const signInWithGoogle = useCallback(async () => {
  const { error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: { redirectTo: window.location.origin },
  })
  if (error) throw error
}, [])
```

Exponerlo en el contexto:
```ts
interface AuthContextValue {
  // ...
  signInWithGoogle: () => Promise<void>
}
```

### 4) Frontend (Login UI)
- Agregar boton primary full-width con icono Google.
- Disparar `signInWithGoogle()` y mostrar estado `loading`.
- Mantener login email/password como secondary (outline).
- Agregar separador + CTA “Acceder como invitado”.

## Manejo de sesion
- `AuthProvider` ya ejecuta `supabase.auth.getSession()` y `onAuthStateChange`.
- Al volver del OAuth, Supabase restaura la sesion en `localStorage`.
- `api.ts` utiliza `VITE_USE_SUPABASE_JWT` para inyectar JWT en requests.

## Manejo de errores
- Mostrar alerta de error si falla OAuth.
- No bloquear login email/password si falla Google.

## Tests
### Manual
1. Click en “Continuar con Google”.
2. Completar OAuth en Google.
3. Verificar redireccion a la app y sesion activa.
4. Confirmar `Authorization: Bearer <token>` en requests si `VITE_USE_SUPABASE_JWT=true`.

### Unit (opcional)
- Mock de `supabase.auth.signInWithOAuth` y verificacion de llamadas.

### E2E (opcional)
- No automatizar OAuth real. Mockear o validar redirect URL.

## Criterios de aceptacion
- Usuario puede iniciar sesion con Google y queda autenticado.
- Sesion persiste tras refresh.
- JWT se inyecta en requests cuando `VITE_USE_SUPABASE_JWT=true`.
- UI del login mantiene el layout de la referencia.

## Riesgos y mitigaciones
- **Redirect URI mal configurado**: validar en Google Cloud + Supabase.
- **CORS o bloqueo en dev**: agregar `http://localhost:5173` en Additional Redirect URLs.
- **JWT no inyectado**: verificar `VITE_USE_SUPABASE_JWT=true`.
