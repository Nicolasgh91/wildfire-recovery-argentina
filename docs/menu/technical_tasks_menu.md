# Tareas técnicas: navegación mobile/tablet + perfil v2

> **Proyecto:** ForestGuard  
> **Fecha:** 2026-02-21  
> **Basado en:** plan revisado SR + análisis crítico validado  
> **Ramas git:** una rama por PR (`feature/pr0-infra-base`, `feature/pr1-nav-source`, etc.)

---

## Reglas generales para el agente

1. **Un commit atómico por tarea** con formato: `PR0-001: create z-index token scale`.
2. **Ejecutar `npm run build` después de cada tarea frontend** — cero warnings nuevos.
3. **Ejecutar `pytest --tb=short` después de cada tarea backend** — cero fallos nuevos.
4. **No agregar dependencias nuevas** salvo indicación explícita.
5. **No modificar URLs públicas de la API** sin redirect 301.
6. Si una tarea rompe el build, **revertir y reportar** antes de continuar.
7. Todos los archivos nuevos usan TypeScript estricto en frontend y type hints en backend.
8. Las traducciones usan la convención de keys existente en `translations.ts` (snake_case con prefijo de sección).

---

## Resumen de esfuerzo

| PR | Tareas | Esfuerzo estimado | Rama git |
|----|--------|-------------------|----------|
| PR0 — Infra base | 7 | ~3 h | `feature/pr0-infra-base` |
| PR1 — Navigation source of truth | 6 | ~4 h | `feature/pr1-nav-source` |
| PR2 — Navegación híbrida mobile/tablet | 8 | ~8 h | `feature/pr2-hybrid-nav` |
| PR3 — Footer links + confirmación externa | 5 | ~3 h | `feature/pr3-footer-integration` |
| PR4 — Perfil v2 (logout + password) | 7 | ~5 h | `feature/pr4-profile-security` |
| PR5 — Delete account backend completo | 12 | ~10 h | `feature/pr5-account-delete` |
| **Total** | **45** | **~33 h** | |

---

## PR0 — Infra base y guardrails

**Rama:** `git checkout -b feature/pr0-infra-base`  
**Dependencias:** ninguna.  
**Gate de salida:** `npm run build` sin warnings, deploy funciona con tag `latest` y por SHA.

---

### PR0-001: crear escala de z-index

**Archivo nuevo:** `frontend/src/features/navigation/config/z-index.ts`  
**Esfuerzo:** 15 min

```typescript
/**
 * Escala centralizada de z-index para evitar colisiones con Leaflet.
 * Leaflet usa internamente z-index hasta ~1000 para tiles/popups/controles.
 * Todos los componentes de navegación y overlays deben usar estos tokens.
 */
export const Z_INDEX = {
  /** Tiles y capas base del mapa */
  MAP_TILES: 0,
  /** Controles del mapa (zoom, ubicación) */
  MAP_CONTROLS: 100,
  /** Overlays del mapa (carrusel de episodios, sidebar lateral) */
  MAP_OVERLAYS: 200,
  /** Barra de navegación fija (bottom nav, topbar) */
  NAVBAR: 300,
  /** Backdrop del Sheet/Drawer */
  DRAWER_BACKDROP: 400,
  /** Contenido del Sheet/Drawer */
  DRAWER_CONTENT: 500,
  /** Modales críticos (confirmación de eliminación, error boundaries) */
  MODAL_CRITICAL: 600,
  /** Toast notifications */
  TOAST: 700,
} as const;

export type ZIndexToken = keyof typeof Z_INDEX;
```

**Verificación:** `npx tsc --noEmit` sin errores.

---

### PR0-002: crear enum de rutas de la aplicación

**Archivo nuevo:** `frontend/src/features/navigation/config/app-routes.ts`  
**Esfuerzo:** 20 min

Extraer todas las rutas definidas en `App.tsx` (lines 60-136) a un enum tipado:

```typescript
/**
 * Rutas internas de la aplicación.
 * Fuente de verdad: debe coincidir 1:1 con las rutas en App.tsx.
 * Si se agrega una ruta en App.tsx, debe agregarse aquí.
 */
export const AppRoutes = {
  HOME: '/home',
  MAP: '/map',
  LOGIN: '/login',
  REGISTER: '/register',
  PROFILE: '/profile',
  FAQ: '/faq',
  MANUAL: '/manual',
  GLOSSARY: '/glossary',
  CONTACT: '/contact',
  EXPLORATION: '/exploracion',
  CITIZEN_REPORT: '/citizen-report',
  FIRES_HISTORY: '/fires/history',
  AUDIT: '/audit',
  CREDITS: '/credits',
  CERTIFICATES: '/certificates',
  SHELTERS: '/shelters',
} as const;

export type AppRoute = (typeof AppRoutes)[keyof typeof AppRoutes];

/**
 * Rutas que requieren autenticación.
 * Debe coincidir con las rutas envueltas en ProtectedRoute en App.tsx.
 */
export const AUTH_REQUIRED_ROUTES: ReadonlySet<AppRoute> = new Set([
  AppRoutes.PROFILE,
  AppRoutes.FIRES_HISTORY,
  AppRoutes.AUDIT,
  AppRoutes.CREDITS,
  AppRoutes.EXPLORATION,
]);
```

**Verificación:** buscar en `App.tsx` todas las rutas con `path=` y confirmar que están en el enum.

```bash
grep -n 'path="/' frontend/src/App.tsx
# Cada ruta encontrada debe tener correspondencia en AppRoutes
```

---

### PR0-003: crear enum de feature flags

**Archivo nuevo:** `frontend/src/features/navigation/config/feature-flags.ts`  
**Esfuerzo:** 15 min

```typescript
/**
 * Feature flags cerrados. No se aceptan strings libres.
 * Para agregar un nuevo flag: añadir aquí + configurar en ENV/backend.
 */
export enum FeatureFlag {
  CERTIFICATES = 'certificates',
  SHELTERS = 'shelters',
}

/**
 * Resolver si un feature flag está activo.
 * MVP: lee de variables de entorno. Post-MVP: puede ser remoto.
 */
export function isFeatureEnabled(flag: FeatureFlag): boolean {
  const envMap: Record<FeatureFlag, string> = {
    [FeatureFlag.CERTIFICATES]: import.meta.env.VITE_FF_CERTIFICATES ?? 'false',
    [FeatureFlag.SHELTERS]: import.meta.env.VITE_FF_SHELTERS ?? 'false',
  };
  return envMap[flag] === 'true';
}
```

---

### PR0-004: crear fallback de navegación para error boundary

**Archivo nuevo:** `frontend/src/features/navigation/components/navigation-error-fallback.tsx`  
**Esfuerzo:** 30 min

Componente que se renderiza si la navegación principal falla. Debe proporcionar acceso mínimo funcional:

```typescript
/**
 * Fallback de navegación que se muestra si el drawer o la navbar fallan.
 * Renderiza links mínimos funcionales: home, mapa, logout.
 * No depende de navigation.ts ni de feature flags para evitar fallo en cascada.
 */
```

Requerimientos:
- Links hardcodeados a `/home`, `/map` y `/login` (no importar de `navigation.ts`).
- Botón de logout que llame directamente a `supabase.auth.signOut()`.
- Estilo mínimo con Tailwind (fondo blanco, links en columna).
- Mensaje visible: "Ocurrió un error en la navegación. Usá estos links para continuar."
- Exportar como componente default.

**Verificación:** importar en `main.tsx` y confirmar que renderiza sin errores cuando se usa como fallback del ErrorBoundary existente.

---

### PR0-005: hacer configurable el tag de imagen frontend en docker-compose

**Archivo a modificar:** `docker-compose.yml`  
**Esfuerzo:** 15 min

Buscar la línea de `image:` del servicio frontend y reemplazar el tag fijo por variable de entorno con fallback:

```yaml
# ANTES (ejemplo, verificar línea real)
image: ghcr.io/<org>/forestguard/frontend:latest

# DESPUÉS
image: ghcr.io/<org>/forestguard/frontend:${FRONTEND_TAG:-latest}
```

**Verificación:**
```bash
# Deploy normal (usa latest)
docker compose up -d frontend

# Deploy por SHA específico (rollback)
FRONTEND_TAG=abc1234 docker compose up -d frontend
```

---

### PR0-006: agregar paso de rollback en deploy.sh

**Archivo a modificar:** `scripts/deploy.sh`  
**Esfuerzo:** 30 min

Agregar función de rollback al final del script:

```bash
# Agregar al inicio del archivo, después de set -euo pipefail:
DEPLOY_LOG="/home/opc/deploy_history.log"

# Agregar antes del pull de imágenes:
PREVIOUS_FRONTEND_SHA=$(docker inspect --format='{{index .Config.Image}}' forestguard-frontend 2>/dev/null || echo "unknown")
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) | deploy_start | previous=$PREVIOUS_FRONTEND_SHA" >> "$DEPLOY_LOG"

# Agregar al final del script:
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) | deploy_complete | current=$(docker inspect --format='{{index .Config.Image}}' forestguard-frontend 2>/dev/null)" >> "$DEPLOY_LOG"
```

**Verificación:** ejecutar deploy y confirmar que `deploy_history.log` registra la imagen anterior y la nueva.

---

### PR0-007: crear runbook de rollback

**Archivo nuevo:** `docs/infrastructure/deployment/frontend-rollback.md`  
**Esfuerzo:** 20 min

Contenido:

```markdown
# Rollback de frontend en producción

## Prerrequisito
Conocer el SHA de la imagen anterior. Consultar:
- `cat /home/opc/deploy_history.log` en la VM
- Tags disponibles: `docker images ghcr.io/<org>/forestguard/frontend`

## Procedimiento
1. SSH a la VM: `ssh opc@<host>`
2. Cambiar tag: `export FRONTEND_TAG=<sha_anterior>`
3. Recrear contenedor: `docker compose up -d frontend`
4. Verificar: `curl -fsS https://localhost/home` (debe cargar)
5. Smoke test: verificar /home, /map, /login en browser

## Restaurar a latest
1. `unset FRONTEND_TAG`
2. `docker compose up -d frontend`
```

---

**Commit final PR0:** `PR0: infrastructure base — z-index, routes, flags, rollback`  
**Checklist antes de merge:**
- [ ] `npm run build` sin warnings nuevos.
- [ ] `docker compose config` parsea sin errores.
- [ ] Nuevo directorio `frontend/src/features/navigation/config/` existe con 4 archivos.
- [ ] `navigation-error-fallback.tsx` renderiza sin errores.

---

## PR1 — Single source of truth de navegación

**Rama:** `git checkout -b feature/pr1-nav-source` (desde PR0 mergeado)  
**Dependencias:** PR0 completado.  
**Gate de salida:** navbar y footer renderizan exactamente los mismos links que hoy; no hay arrays duplicados.

---

### PR1-001: crear configuración central de navegación

**Archivo nuevo:** `frontend/src/features/navigation/config/navigation.ts`  
**Esfuerzo:** 1.5 h

Definir el contrato de navegación con tipos discriminados:

```typescript
import { AppRoute, AppRoutes } from './app-routes';
import { FeatureFlag } from './feature-flags';

export type NavigationSection = 'explore' | 'tools' | 'account' | 'help';

export type NavigationVisibility = 'always' | 'auth_only' | 'guest_only';

interface BaseNavigationItem {
  id: string;
  section: NavigationSection;
  labelKey: string; // key de i18n en translations.ts
  icon?: string; // nombre del ícono de lucide-react
  visibility: NavigationVisibility;
  order: number;
}

export interface InternalNavItem extends BaseNavigationItem {
  kind: 'internal';
  path: AppRoute;
  featureFlag?: FeatureFlag;
  /** true = NavLink usa prop `end` (match exacto). Default false. */
  matchExact: boolean;
}

export interface ExternalNavItem extends BaseNavigationItem {
  kind: 'external';
  href: string;
  requiresExitConfirm: boolean;
}

export type NavigationItem = InternalNavItem | ExternalNavItem;
```

Definir el array completo con todos los ítems actuales de navbar + footer. Extraer de:
- `navbar.tsx` line 37 (`navItems` array).
- `footer.tsx` lines 27-47 (secciones producto, soporte, informativos, fuentes públicas).

**Reglas de visibilidad:**
- `always`: home, map, exploración, citizen-report, faq, manual, glossary, contact, fuentes públicas externas.
- `auth_only`: fires/history, audit, profile, credits, logout.
- `guest_only`: login, register.
- Feature flags: certificates (FeatureFlag.CERTIFICATES), shelters (FeatureFlag.SHELTERS).

**Regla de matchExact:**
- Rutas que pueden tener hijos dinámicos (`/fires/history`, `/exploracion`) usan `matchExact: false`.
- Rutas terminales (`/home`, `/map`, `/profile`, `/faq`) usan `matchExact: true`.

Exportar funciones helper:

```typescript
export function getVisibleItems(
  section: NavigationSection,
  isAuthenticated: boolean,
): NavigationItem[] { ... }

export function getInternalItems(items: NavigationItem[]): InternalNavItem[] { ... }

export function getExternalItems(items: NavigationItem[]): ExternalNavItem[] { ... }
```

---

### PR1-002: reservar todas las keys de i18n

**Archivo a modificar:** `frontend/src/data/translations.ts`  
**Esfuerzo:** 30 min

Agregar todas las keys de navegación y perfil necesarias para PR1-PR5. Las que aún no se usen llevan valor descriptivo de placeholder:

```typescript
// Sección nav_ (PR1)
nav_explore: 'Explorar',
nav_tools: 'Herramientas',
nav_account: 'Cuenta',
nav_help: 'Ayuda',
nav_home: 'Inicio',
nav_map: 'Mapa',
nav_exploration: 'Exploración',
nav_citizen_report: 'Reporte ciudadano',
nav_fires_history: 'Historial de incendios',
nav_audit: 'Auditoría',
nav_credits: 'Créditos',
nav_certificates: 'Certificados',
nav_shelters: 'Refugios',
nav_faq: 'Preguntas frecuentes',
nav_manual: 'Manual',
nav_glossary: 'Glosario',
nav_contact: 'Contacto',
nav_menu: 'Menú',

// Sección nav_external_ (PR3)
nav_external_confirm_title: 'Salir de ForestGuard',
nav_external_confirm_message: 'Estás por visitar un sitio externo. ¿Querés continuar?',
nav_external_confirm_yes: 'Continuar',
nav_external_confirm_no: 'Cancelar',

// Sección account_ (PR4)
account_logout: 'Cerrar sesión',
account_logout_success: 'Sesión cerrada correctamente',
account_update_password: 'Actualizar contraseña',
account_current_password: 'Contraseña actual',
account_new_password: 'Nueva contraseña',
account_confirm_password: 'Confirmar contraseña',
account_password_updated: 'Contraseña actualizada correctamente',
account_password_error: 'No se pudo actualizar la contraseña. Verificá tu contraseña actual.',
account_password_reset_sent: 'Si existe una cuenta asociada a este correo, recibirás un enlace para restablecer tu contraseña.',
account_session_expired: 'Tu sesión expiró. Por favor, volvé a iniciar sesión.',
account_security: 'Seguridad de la cuenta',

// Sección account_delete_ (PR5)
account_delete: 'Eliminar cuenta',
account_delete_title: 'Eliminar cuenta permanentemente',
account_delete_warning: 'Esta acción es irreversible. Se eliminarán tus datos personales y se cerrará tu sesión.',
account_delete_type_confirm: 'Escribí ELIMINAR para confirmar',
account_delete_type_email: 'Escribí tu email para confirmar',
account_delete_enter_password: 'Ingresá tu contraseña actual',
account_delete_success: 'Tu cuenta fue eliminada. Redirigiendo...',
account_delete_error: 'No se pudo eliminar la cuenta. Intentá nuevamente.',
account_delete_challenge_sent: 'Te enviamos un email de confirmación. Revisá tu bandeja de entrada.',
```

Hacer lo mismo para la key equivalente en inglés si el archivo tiene soporte i18n dual.

**Verificación:** `npm run build` — no debe haber keys faltantes referenciadas desde componentes.

---

### PR1-003: migrar navbar a consumir navigation.ts

**Archivo a modificar:** `frontend/src/components/layout/navbar.tsx`  
**Esfuerzo:** 45 min

Cambios:
1. Eliminar el array `navItems` hardcodeado (line 37 aproximada).
2. Importar `getVisibleItems` de `navigation.ts`.
3. Reemplazar `pathname === ...` por `NavLink` de react-router-dom con prop `end` según `matchExact`.
4. Obtener estado de autenticación desde `useAuth()` existente.
5. Filtrar ítems visibles: `getVisibleItems('explore', isAuthenticated)`.

**No tocar:** la estructura HTML/CSS de desktop navbar (`hidden md:flex`). Solo cambiar la fuente de datos.

**Verificación:**
```bash
# Verificar que no quedan arrays hardcodeados de links
grep -n "navItems\|menuItems\|links =" frontend/src/components/layout/navbar.tsx
# Debe retornar vacío o solo imports de navigation.ts
```

Regresión visual: abrir `/home`, `/map`, `/faq` en desktop y confirmar que los links son idénticos a antes.

---

### PR1-004: migrar footer a consumir navigation.ts

**Archivo a modificar:** `frontend/src/components/layout/footer.tsx`  
**Esfuerzo:** 45 min

Cambios:
1. Eliminar los arrays de links internos hardcodeados (lines 27-47 aproximadas).
2. Importar `getVisibleItems`, `getInternalItems`, `getExternalItems` de `navigation.ts`.
3. Renderizar secciones del footer usando las mismas categorías de `NavigationSection`.
4. Para links externos: mantener el comportamiento actual de `window.open` con `confirm` pero extraerlo a una función reutilizable que será reemplazada en PR3 por `ExternalConfirmDialog`.

**No tocar:** estilos CSS ni la visibilidad responsive (`hidden md:block`).

**Verificación:** abrir footer en desktop y confirmar links idénticos a antes.

---

### PR1-005: crear test de cobertura de rutas

**Archivo nuevo:** `frontend/src/features/navigation/__tests__/navigation-config.test.ts`  
**Esfuerzo:** 30 min

```typescript
import { describe, it, expect } from 'vitest';
import { NAVIGATION_ITEMS } from '../config/navigation';
import { AppRoutes } from '../config/app-routes';
import { FeatureFlag } from '../config/feature-flags';

describe('navigation config', () => {
  it('every internal item references a valid AppRoute', () => {
    const validRoutes = new Set(Object.values(AppRoutes));
    const internalItems = NAVIGATION_ITEMS.filter(i => i.kind === 'internal');
    for (const item of internalItems) {
      expect(validRoutes.has(item.path)).toBe(true);
    }
  });

  it('every featureFlag references a valid FeatureFlag enum', () => {
    const validFlags = new Set(Object.values(FeatureFlag));
    const flaggedItems = NAVIGATION_ITEMS.filter(
      i => i.kind === 'internal' && i.featureFlag
    );
    for (const item of flaggedItems) {
      expect(validFlags.has(item.featureFlag!)).toBe(true);
    }
  });

  it('no duplicate item ids', () => {
    const ids = NAVIGATION_ITEMS.map(i => i.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('all sections have at least one item', () => {
    const sections = new Set(NAVIGATION_ITEMS.map(i => i.section));
    expect(sections.size).toBeGreaterThanOrEqual(4);
  });
});
```

**Verificación:** `npx vitest run src/features/navigation/__tests__/` — todos pasan.

---

### PR1-006: ajustar App.tsx para importar rutas tipadas

**Archivo a modificar:** `frontend/src/App.tsx`  
**Esfuerzo:** 20 min

Reemplazar los strings de rutas hardcodeados por constantes de `AppRoutes`:

```typescript
// ANTES
<Route path="/home" element={<HomePage />} />

// DESPUÉS
import { AppRoutes } from './features/navigation/config/app-routes';
<Route path={AppRoutes.HOME} element={<HomePage />} />
```

Aplicar a todas las rutas en App.tsx. Los strings que no estén en AppRoutes son un error de compilación intencional.

**Verificación:** `npx tsc --noEmit` sin errores. Navegar a `/home`, `/map`, `/profile` en browser.

---

**Commit final PR1:** `PR1: single source of truth — navigation config + typed routes`  
**Checklist antes de merge:**
- [ ] No hay arrays de links duplicados entre navbar.tsx / footer.tsx.
- [ ] Todos los links internos compilan contra `AppRoute`.
- [ ] Feature flags solo aceptan valores del enum `FeatureFlag`.
- [ ] Tests de `navigation-config.test.ts` pasan.
- [ ] Regresión visual: navbar y footer desktop renderizan los mismos links que antes.

---

## PR2 — Navegación híbrida mobile/tablet

**Rama:** `git checkout -b feature/pr2-hybrid-nav` (desde PR1 mergeado)  
**Dependencias:** PR1 completado.  
**Gate de salida:** UX híbrida funcional en `<md` / `md-<lg` / `>=lg` sin regresiones en MapPage.

---

### PR2-001: crear bottom nav para mobile

**Archivo nuevo:** `frontend/src/features/navigation/components/navigation-bottom-nav.tsx`  
**Esfuerzo:** 1 h

Componente de barra inferior fija para viewports `<md` (< 768px). 4 slots:

| Slot | Ruta/acción | Ícono (lucide-react) |
|------|-------------|---------------------|
| 1 | `/home` | `Home` |
| 2 | `/map` | `Map` |
| 3 | `/exploracion` | `Search` |
| 4 | Abre drawer | `Menu` |

Requerimientos:
- Clase `fixed bottom-0 left-0 right-0` con `z-index` de token `Z_INDEX.NAVBAR`.
- Clase responsive `md:hidden` (solo visible en mobile).
- Cada slot usa `NavLink` con active state visual (color primario del tema).
- Slot 4 dispara el estado `isDrawerOpen` del componente padre.
- Tap targets mínimo `44px` de alto: usar `h-11 min-h-[44px]`.
- Cada botón tiene `aria-label` con el texto de la acción.
- Safe area padding inferior: `pb-safe` o `pb-[env(safe-area-inset-bottom)]`.

**Verificación:** viewport 390x844 en DevTools, confirmar 4 íconos en bottom, tap targets >= 44px.

---

### PR2-002: crear navigation drawer (Sheet)

**Archivo nuevo:** `frontend/src/features/navigation/components/navigation-drawer.tsx`  
**Esfuerzo:** 1.5 h

Drawer lateral basado en `Sheet` de shadcn (ya importado en el proyecto). Se abre desde el slot "menú" de bottom nav o desde el botón hamburguesa en tablet.

Requerimientos:
- Usar `Sheet` con `side="left"`.
- Importar `getVisibleItems` de `navigation.ts` para renderizar secciones.
- Secciones separadas por `NavigationSection` con título visual.
- Links internos usan `NavLink` con `end` según `matchExact`. Al hacer click en un link, cerrar el drawer.
- Links externos muestran ícono de `ExternalLink` de lucide-react (la confirmación se agrega en PR3).
- Incluir toggle de idioma y toggle de tema (moverlos desde `navbar.tsx` lines 99/117 al drawer).
- Incluir botón de logout visible solo para usuarios autenticados.
- Aplicar `z-index` de tokens `Z_INDEX.DRAWER_BACKDROP` y `Z_INDEX.DRAWER_CONTENT`.
- Scroll interno: `overflow-y-auto` en el contenido del drawer, `max-h-[100dvh]`.

Props:

```typescript
interface NavigationDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}
```

**Verificación:**
- Abrir drawer: foco queda dentro (focus trap de Radix).
- Presionar `Esc`: cierra y foco vuelve al botón trigger.
- Scroll del body bloqueado con drawer abierto.
- Probar en viewport 390x844 y 768x1024.

---

### PR2-003: crear topbar para tablet

**Archivo nuevo:** `frontend/src/features/navigation/components/navigation-topbar-tablet.tsx`  
**Esfuerzo:** 30 min

Barra superior para viewports `md` a `<lg` (768px - 1023px). Contiene:
- Logo a la izquierda.
- Botón hamburguesa a la derecha que abre el drawer.
- Clase responsive `hidden md:flex lg:hidden`.
- `z-index` de token `Z_INDEX.NAVBAR`.
- Botón hamburguesa con `aria-label="Abrir menú de navegación"`.

---

### PR2-004: componer componentes en navbar.tsx

**Archivo a modificar:** `frontend/src/components/layout/navbar.tsx`  
**Esfuerzo:** 1 h

Refactorizar navbar para componer los tres componentes según breakpoint:

```tsx
export function Navbar() {
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <>
      {/* Mobile: bottom nav + drawer */}
      <NavigationBottomNav onMenuPress={() => setDrawerOpen(true)} />

      {/* Tablet: topbar + drawer */}
      <NavigationTopbarTablet onMenuPress={() => setDrawerOpen(true)} />

      {/* Desktop: navbar actual sin cambios funcionales */}
      <DesktopNavbar /> {/* extraer la sección hidden md:flex actual */}

      {/* Drawer compartido mobile/tablet */}
      <NavigationDrawer open={drawerOpen} onOpenChange={setDrawerOpen} />
    </>
  );
}
```

**Cambios:**
1. Eliminar la bottom nav fija actual (`md:hidden`, line 164 aprox.).
2. Mover toggle de idioma/tema de desktop a drawer (siguen accesibles en desktop vía dropdown existente).
3. Mover `signOut` de dropdown desktop al drawer (PR4 lo agrega también a Profile).

**No tocar:** estilos visuales de la navbar desktop (`hidden md:flex lg:flex`).

---

### PR2-005: ajustar z-index en MapPage

**Archivo a modificar:** `frontend/src/pages/MapPage.tsx`  
**Esfuerzo:** 30 min

Cambios:
1. Importar `Z_INDEX` de `z-index.ts`.
2. Overlay desktop lateral (line 150 aprox.): asignar `style={{ zIndex: Z_INDEX.MAP_OVERLAYS }}`.
3. Carrusel mobile por cards (line 218 aprox.): asignar `style={{ zIndex: Z_INDEX.MAP_OVERLAYS }}`.
4. Botón mobile de mostrar/ocultar sidebar (line 143 aprox.): agregar `aria-label="Mostrar panel de episodios"`.

**Verificación:** abrir `/map` en viewport 390x844, abrir drawer, confirmar que el drawer está sobre el mapa y el carrusel. Cerrar drawer, confirmar que carrusel y controles del mapa siguen funcionales.

---

### PR2-006: ajustar Sheet para z-index y scroll lock

**Archivo a modificar:** `frontend/src/components/ui/sheet.tsx`  
**Esfuerzo:** 20 min

Agregar clases de z-index controladas:
1. En el `SheetOverlay`: agregar estilo con `Z_INDEX.DRAWER_BACKDROP`.
2. En el `SheetContent`: agregar estilo con `Z_INDEX.DRAWER_CONTENT`.
3. En el `SheetContent`: agregar `overscroll-behavior: contain` para mitigar scroll bleed en iOS Safari.

**No tocar:** la API pública del componente Sheet (props, exports).

---

### PR2-007: crear test de navegación mobile

**Archivo nuevo:** `frontend/src/features/navigation/__tests__/navigation-drawer.test.tsx`  
**Esfuerzo:** 45 min

Tests con Vitest + Testing Library:

```typescript
describe('NavigationDrawer', () => {
  it('renders all visible sections for authenticated user');
  it('renders only public items for guest user');
  it('closes on NavLink click');
  it('closes on Escape key');
  it('has focus trap when open');
  it('returns focus to trigger on close');
  it('does not show auth-only items when logged out');
  it('does not show guest-only items when logged in');
});
```

---

### PR2-008: crear spec E2E de navegación mobile

**Archivo nuevo:** `frontend/tests/ui/navigation.mobile.spec.ts`  
**Esfuerzo:** 45 min

Tests con Playwright:

```typescript
import { test, expect } from '@playwright/test';

test.describe('mobile navigation', () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test('bottom nav shows 4 slots', async ({ page }) => {
    await page.goto('/home');
    // verificar 4 botones en bottom nav
  });

  test('menu button opens drawer', async ({ page }) => {
    await page.goto('/home');
    await page.getByRole('button', { name: /menú/i }).click();
    // verificar drawer visible con secciones
  });

  test('drawer closes on Escape', async ({ page }) => { ... });

  test('map page usable with drawer closed', async ({ page }) => {
    await page.goto('/map');
    // verificar que controles del mapa son clickeables
  });

  test('map page: drawer overlays map correctly', async ({ page }) => {
    await page.goto('/map');
    await page.getByRole('button', { name: /menú/i }).click();
    // verificar que drawer está sobre el mapa (z-index)
  });
});

test.describe('tablet navigation', () => {
  test.use({ viewport: { width: 768, height: 1024 } });

  test('shows topbar with hamburger, not bottom nav', async ({ page }) => { ... });
});

test.describe('desktop navigation', () => {
  test.use({ viewport: { width: 1366, height: 768 } });

  test('shows horizontal navbar, no hamburger', async ({ page }) => { ... });
});
```

---

**Commit final PR2:** `PR2: hybrid navigation — bottom nav + drawer + tablet topbar`  
**Checklist antes de merge:**
- [ ] `<md`: bottom nav con 4 slots, drawer al presionar "menú".
- [ ] `md` a `<lg`: topbar con hamburguesa, drawer al presionar.
- [ ] `>=lg`: navbar desktop sin cambios.
- [ ] Drawer siempre sobre overlays del mapa (verificar z-index).
- [ ] Focus trap, ESC y scroll lock funcionan.
- [ ] Toggle idioma/tema accesibles en drawer.
- [ ] `npm run build` sin warnings.

---

## PR3 — Integrar links del footer al menú

**Rama:** `git checkout -b feature/pr3-footer-integration` (desde PR2 mergeado)  
**Dependencias:** PR2 completado.  
**Gate de salida:** todos los links del footer accesibles en mobile vía drawer.

---

### PR3-001: crear componente de confirmación externa

**Archivo nuevo:** `frontend/src/features/navigation/components/external-confirm-dialog.tsx`  
**Esfuerzo:** 45 min

Dialog modal reutilizable para confirmar navegación a sitio externo. Usa `AlertDialog` de shadcn/Radix.

Props:
```typescript
interface ExternalConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  href: string;
  siteName: string;
}
```

Comportamiento:
- Muestra URL destino.
- Botón "Continuar" abre `window.open(href, '_blank', 'noopener,noreferrer')`.
- Botón "Cancelar" cierra el dialog.
- `z-index` de `Z_INDEX.MODAL_CRITICAL`.

---

### PR3-002: crear componente de secciones del menú

**Archivo nuevo:** `frontend/src/features/navigation/components/navigation-menu-sections.tsx`  
**Esfuerzo:** 45 min

Componente que renderiza los ítems de navegación agrupados por sección. Se usa tanto en el drawer como referencia para el footer:

```typescript
interface NavigationMenuSectionsProps {
  sections: NavigationSection[];
  isAuthenticated: boolean;
  onInternalNavigate: (path: string) => void;
  onExternalClick: (item: ExternalNavItem) => void;
}
```

- Cada sección tiene un título visual (`<h3>` con className `text-sm font-semibold text-muted-foreground`).
- Items renderizados en lista vertical.
- Items externos muestran ícono `ExternalLink` a la derecha.

---

### PR3-003: integrar secciones en navigation-drawer

**Archivo a modificar:** `frontend/src/features/navigation/components/navigation-drawer.tsx`  
**Esfuerzo:** 30 min

Reemplazar el rendering directo de links por `NavigationMenuSections`. Agregar estado para `ExternalConfirmDialog`:

```typescript
const [externalTarget, setExternalTarget] = useState<ExternalNavItem | null>(null);

// En render:
<NavigationMenuSections
  sections={['explore', 'tools', 'account', 'help']}
  isAuthenticated={isAuthenticated}
  onInternalNavigate={(path) => { navigate(path); onOpenChange(false); }}
  onExternalClick={(item) => {
    if (item.requiresExitConfirm) setExternalTarget(item);
    else window.open(item.href, '_blank', 'noopener,noreferrer');
  }}
/>

<ExternalConfirmDialog
  open={!!externalTarget}
  onOpenChange={() => setExternalTarget(null)}
  href={externalTarget?.href ?? ''}
  siteName={externalTarget?.labelKey ?? ''}
/>
```

---

### PR3-004: unificar confirmación externa en footer

**Archivo a modificar:** `frontend/src/components/layout/footer.tsx`  
**Esfuerzo:** 30 min

Reemplazar las dos variantes actuales de apertura externa:
- `window.open` con `confirm` (line 65 aprox.)
- `<a>` directo (line 159 aprox.)

Por una sola variante: importar `ExternalConfirmDialog` y manejar el click con el mismo patrón que en el drawer.

**Verificación:** en desktop, hacer click en un link externo del footer. Debe aparecer el dialog de confirmación en lugar del `window.confirm()` nativo.

---

### PR3-005: test de confirmación externa

**Archivo nuevo:** agregar tests en `frontend/src/features/navigation/__tests__/navigation-drawer.test.tsx` (extender el archivo existente de PR2-007).  
**Esfuerzo:** 30 min

```typescript
describe('external confirm dialog', () => {
  it('opens dialog on external link click');
  it('opens external URL on confirm');
  it('closes dialog on cancel');
  it('uses noopener,noreferrer on window.open');
});
```

---

**Commit final PR3:** `PR3: footer links in drawer + uniform external confirmation`  
**Checklist:**
- [ ] Todos los links del footer accesibles en mobile vía drawer.
- [ ] Confirmación externa uniforme en footer y drawer.
- [ ] No hay duplicaciones incoherentes navbar/menu/footer.
- [ ] Feature flags respetados.
- [ ] Auth/guest visibility correcta por sección.

---

## PR4 — Perfil v2 (logout + password)

**Rama:** `git checkout -b feature/pr4-profile-security` (desde PR3 mergeado)  
**Dependencias:** PR3 completado.  
**Gate de salida:** reauth obligatoria antes de cambio de password; mensajes anti-enumeración.

---

### PR4-001: crear hook useAccountActions

**Archivo nuevo:** `frontend/src/features/account/hooks/use-account-actions.ts`  
**Esfuerzo:** 1 h

```typescript
import { supabase } from '@/lib/supabase';

interface AccountActionsResult {
  /** Reautentica con contraseña actual. Necesario antes de updatePassword. */
  reauthenticate: (currentPassword: string) => Promise<{ success: boolean; error?: string }>;
  /** Actualiza contraseña. Requiere reauthenticate exitoso previo. */
  updatePassword: (newPassword: string) => Promise<{ success: boolean; error?: string }>;
  /** Envía email de reset. Mensaje neutro siempre, sin importar si el email existe. */
  sendPasswordReset: (email: string) => Promise<{ success: boolean }>;
  /** Logout global. */
  logout: () => Promise<void>;
  /** Estado de loading para UX. */
  isLoading: boolean;
}
```

Implementación de `reauthenticate`:
```typescript
async function reauthenticate(currentPassword: string) {
  const { data: { user } } = await supabase.auth.getUser();
  if (!user?.email) return { success: false, error: 'session_expired' };

  const { error } = await supabase.auth.signInWithPassword({
    email: user.email,
    password: currentPassword,
  });

  if (error) return { success: false, error: 'invalid_password' };
  return { success: true };
}
```

Implementación de `updatePassword`:
```typescript
async function updatePassword(newPassword: string) {
  const { error } = await supabase.auth.updateUser({ password: newPassword });
  if (error) return { success: false, error: error.message };
  return { success: true };
}
```

Implementación de `sendPasswordReset`:
```typescript
async function sendPasswordReset(email: string) {
  // Siempre retorna success para evitar enumeración de emails.
  await supabase.auth.resetPasswordForEmail(email).catch(() => {});
  return { success: true };
}
```

**No importar ni modificar AuthContext.** Este hook consume `supabase` directamente.

---

### PR4-002: crear componente de tarjeta de seguridad

**Archivo nuevo:** `frontend/src/features/account/components/password-security-card.tsx`  
**Esfuerzo:** 1 h

Card dentro de la página de perfil con las acciones de seguridad.

Contenido:
- Título: "Seguridad de la cuenta" (key `account_security`).
- Formulario de cambio de contraseña:
  - Input de contraseña actual (requerido).
  - Input de nueva contraseña (requerido, min 8 caracteres).
  - Input de confirmación (debe coincidir).
  - Botón "Actualizar contraseña".
- Link "¿Olvidaste tu contraseña?" que ejecuta `sendPasswordReset(user.email)`.
- Cooldown visible de 30 segundos después de enviar reset.

Flujo al presionar "Actualizar":
1. Llamar `reauthenticate(currentPassword)`.
2. Si falla: mostrar error genérico (key `account_password_error`).
3. Si éxito: llamar `updatePassword(newPassword)`.
4. Si falla: mostrar error genérico.
5. Si éxito: mostrar toast (key `account_password_updated`), limpiar formulario.

**Para usuarios OAuth (sin password_hash):** detectar vía `user.app_metadata.provider`. Si no es `email`, ocultar el formulario de cambio de contraseña y mostrar mensaje: "Tu cuenta usa inicio de sesión con Google. Para cambiar tu contraseña, gestionala desde tu cuenta de Google."

Accesibilidad:
- `aria-live="polite"` en la zona de mensajes de feedback.
- Botón muestra spinner durante loading.

---

### PR4-003: crear componente de acción de logout

**Archivo nuevo:** `frontend/src/features/account/components/logout-action.tsx`  
**Esfuerzo:** 20 min

Botón de logout reutilizable:

```typescript
export function LogoutAction({ variant = 'ghost' }: { variant?: 'ghost' | 'destructive' }) {
  const { logout } = useAccountActions();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate(AppRoutes.LOGIN);
  };

  return (
    <Button variant={variant} onClick={handleLogout}>
      <LogOut className="h-4 w-4 mr-2" />
      {t('account_logout')}
    </Button>
  );
}
```

---

### PR4-004: integrar componentes en Profile.tsx

**Archivo a modificar:** `frontend/src/pages/Profile.tsx`  
**Esfuerzo:** 30 min

Agregar debajo del formulario de metadata existente (line 33 aprox.):
1. `<PasswordSecurityCard />` — card de seguridad.
2. `<LogoutAction variant="destructive" />` — botón de logout.
3. Placeholder deshabilitado para eliminar cuenta (PR5): botón con `disabled` y `title="Próximamente"`.

**No tocar:** el formulario existente de update metadata.

---

### PR4-005: agregar logout al drawer mobile

**Archivo a modificar:** `frontend/src/features/navigation/components/navigation-drawer.tsx`  
**Esfuerzo:** 15 min

En la sección "Cuenta" del drawer, agregar `<LogoutAction variant="ghost" />` al final, visible solo para usuarios autenticados.

---

### PR4-006: crear tests de seguridad del perfil

**Archivo nuevo:** `frontend/src/features/account/__tests__/use-account-actions.test.ts`  
**Esfuerzo:** 45 min

```typescript
describe('useAccountActions', () => {
  it('reauthenticate succeeds with correct password');
  it('reauthenticate fails with incorrect password');
  it('updatePassword requires prior reauthenticate');
  it('sendPasswordReset always returns success (anti-enumeration)');
  it('logout calls supabase.auth.signOut');
});
```

**Archivo nuevo:** `frontend/src/features/account/__tests__/profile-security.test.tsx`  
**Esfuerzo:** 30 min

```typescript
describe('PasswordSecurityCard', () => {
  it('shows password form for email/password users');
  it('hides password form for OAuth users');
  it('shows error on wrong current password');
  it('shows success toast on password update');
  it('enforces 30s cooldown on reset link');
  it('does not expose sensitive info in error messages');
});
```

---

### PR4-007: crear spec E2E de perfil

**Archivo nuevo:** `frontend/tests/ui/profile.security.spec.ts`  
**Esfuerzo:** 30 min

```typescript
test.describe('profile security', () => {
  test('logout redirects to /login');
  test('password update requires current password');
  test('password reset shows neutral message');
  test('OAuth user does not see password form');
});
```

---

**Commit final PR4:** `PR4: profile v2 — reauth + password update + logout`  
**Checklist:**
- [ ] No se puede cambiar password sin reauth reciente.
- [ ] Mensajes de error no filtran detalles sensibles.
- [ ] `aria-live` en feedback de acciones críticas.
- [ ] Logout funciona desde perfil y desde drawer mobile.
- [ ] Redirect post-logout a `/login`.
- [ ] Tests P0 (seguridad) pasan.

---

## PR5 — Delete account backend completo

**Rama:** `git checkout -b feature/pr5-account-delete` (desde PR4 mergeado)  
**Dependencias:** PR4 completado.  
**Gate de salida:** usuario eliminado no puede autenticarse; audit trail persistido; FKs alineadas.

---

### PR5-001: preflight SQL de foreign keys

**Ejecutar manualmente antes de cualquier migración.**  
**Esfuerzo:** 15 min

```sql
-- Verificar FKs hacia users(id) y su política ON DELETE
SELECT
  tc.table_name,
  kcu.column_name,
  rc.delete_rule
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.referential_constraints rc
  ON tc.constraint_name = rc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND kcu.column_name LIKE '%user%'
ORDER BY tc.table_name;
```

**Resultado esperado (según rectificaciones del plan):**

| Tabla | Columna | ON DELETE actual |
|-------|---------|-----------------|
| `user_saved_filters` | `user_id` | CASCADE ✅ |
| `user_investigations` | `user_id` | CASCADE ✅ |
| `citizen_reports` | `reporter_user_id` | ¿? → verificar |

**Regla cerrada:** si `citizen_reports.reporter_user_id` no tiene `ON DELETE SET NULL`, la migración PR5-002 lo agrega. Los reportes ciudadanos se preservan con `reporter_user_id = NULL`.

---

### PR5-002: migración de campos de soft-delete en users

**Archivo nuevo:** `database/migrations/2026_02_21_add_user_soft_delete_fields.sql`  
**Esfuerzo:** 15 min

```sql
-- Campos para soft-delete y anonimización
ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS is_deleted boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS deleted_at timestamp with time zone,
  ADD COLUMN IF NOT EXISTS deletion_reason text;

-- Índice parcial para excluir usuarios eliminados de queries normales
CREATE INDEX IF NOT EXISTS idx_users_active
  ON public.users (id) WHERE is_deleted = false;

COMMENT ON COLUMN public.users.is_deleted IS 'Soft-delete flag. Usuario borrado lógicamente.';
COMMENT ON COLUMN public.users.deleted_at IS 'Timestamp de eliminación.';
COMMENT ON COLUMN public.users.deletion_reason IS 'Motivo de eliminación (user_request, admin, etc).';
```

---

### PR5-003: migración condicional de FKs

**Archivo nuevo:** `database/migrations/2026_02_21_account_delete_fk_alignment.sql`  
**Esfuerzo:** 10 min

Solo se ejecuta si el preflight PR5-001 detectó que `citizen_reports` no tiene `ON DELETE SET NULL`:

```sql
-- Alinear FK de citizen_reports para preservar reportes al eliminar usuario
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.referential_constraints rc
    JOIN information_schema.key_column_usage kcu
      ON rc.constraint_name = kcu.constraint_name
    WHERE kcu.table_name = 'citizen_reports'
      AND kcu.column_name = 'reporter_user_id'
      AND rc.delete_rule != 'SET NULL'
  ) THEN
    ALTER TABLE public.citizen_reports
      DROP CONSTRAINT IF EXISTS citizen_reports_reporter_user_id_fkey;
    ALTER TABLE public.citizen_reports
      ADD CONSTRAINT citizen_reports_reporter_user_id_fkey
        FOREIGN KEY (reporter_user_id) REFERENCES public.users(id)
        ON DELETE SET NULL;
  END IF;
END $$;
```

---

### PR5-004: agregar SUPABASE_SERVICE_KEY en config backend

**Archivo a modificar:** `app/core/config.py`  
**Esfuerzo:** 10 min

Agregar en la clase `Settings`:

```python
SUPABASE_SERVICE_KEY: str = Field(
    default="",
    description="Supabase service role key. NEVER expose to frontend. Required for account deletion."
)
```

**Archivo a modificar:** `.env.template`

Agregar:
```bash
SUPABASE_SERVICE_KEY=<CHANGE_ME_supabase_service_role_key>
```

**Verificación:** `python -c "from app.core.config import settings; print(bool(settings.SUPABASE_SERVICE_KEY))"` — retorna True si configurado.

---

### PR5-005: crear servicio de Supabase Admin

**Archivo nuevo:** `app/services/supabase_admin.py`  
**Esfuerzo:** 1 h

```python
"""
Wrapper para Supabase Admin API.
Usa service_role key exclusivamente server-side.
"""
from supabase import create_client, Client
from app.core.config import settings

def get_admin_client() -> Client:
    if not settings.SUPABASE_SERVICE_KEY:
        raise RuntimeError("SUPABASE_SERVICE_KEY not configured")
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_KEY,
    )

async def revoke_all_sessions(user_id: str) -> None:
    """Revoca todas las sesiones activas de un usuario."""
    client = get_admin_client()
    client.auth.admin.sign_out(user_id, scope="global")

async def delete_auth_user(user_id: str) -> None:
    """Elimina la identidad del usuario en Supabase Auth."""
    client = get_admin_client()
    client.auth.admin.delete_user(user_id)
```

---

### PR5-006: crear servicio de eliminación de cuenta

**Archivo nuevo:** `app/services/account_service.py`  
**Esfuerzo:** 1.5 h

```python
"""
Servicio de eliminación de cuenta.
Flujo: soft-delete local → anonimización PII → revocación Supabase → audit.
"""
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

async def soft_delete_account(
    db: AsyncSession,
    user_id: str,
    reason: str = "user_request",
) -> None:
    """
    1. Anonimizar PII en tabla users.
    2. Marcar como eliminado.
    3. Revocar sesiones en Supabase.
    4. Eliminar identidad en Supabase Auth.
    5. Registrar evento de auditoría.
    """
    anonymous_token = f"deleted_{uuid4().hex[:12]}"

    # 1. Anonimizar
    await db.execute(
        text("""
            UPDATE users SET
                email = :anon_email,
                full_name = 'Usuario eliminado',
                password_hash = NULL,
                dni = NULL,
                google_id = NULL,
                avatar_url = NULL,
                is_deleted = true,
                deleted_at = :now,
                deletion_reason = :reason
            WHERE id = :user_id AND is_deleted = false
        """),
        {
            "anon_email": f"{anonymous_token}@deleted.forestguard.local",
            "user_id": user_id,
            "now": datetime.now(timezone.utc),
            "reason": reason,
        }
    )

    # 2. Revocar sesiones
    from app.services.supabase_admin import revoke_all_sessions, delete_auth_user
    await revoke_all_sessions(user_id)

    # 3. Eliminar identidad en Supabase Auth
    await delete_auth_user(user_id)

    # 4. Audit event
    await db.execute(
        text("""
            INSERT INTO audit_events (principal_id, action, resource_type, resource_id, details)
            VALUES (:user_id, 'account_deleted', 'user', :user_id_uuid, :details)
        """),
        {
            "user_id": user_id,
            "user_id_uuid": user_id,
            "details": json.dumps({
                "reason": reason,
                "anonymized_to": anonymous_token,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }),
        }
    )

    await db.commit()
```

---

### PR5-007: crear schemas de request/response

**Archivo nuevo:** `app/schemas/account.py`  
**Esfuerzo:** 20 min

```python
from pydantic import BaseModel, Field

class DeleteAccountChallengeRequest(BaseModel):
    """Solicita un token de challenge por email (para usuarios OAuth)."""
    pass  # No acepta user_id; se toma del JWT

class DeleteAccountChallengeResponse(BaseModel):
    message: str = "Si la cuenta existe, se envió un email de confirmación."

class DeleteAccountRequest(BaseModel):
    """Confirma la eliminación de cuenta."""
    confirmation_text: str = Field(..., pattern=r"^ELIMINAR$")
    confirmation_email: str = Field(..., max_length=320)
    current_password: str | None = Field(None, min_length=1, max_length=128)
    challenge_token: str | None = Field(None, max_length=64)

class DeleteAccountResponse(BaseModel):
    message: str = "Cuenta eliminada correctamente."
```

---

### PR5-008: crear endpoint de eliminación de cuenta

**Archivo nuevo:** `app/api/v1/account.py`  
**Esfuerzo:** 1.5 h

```python
from fastapi import APIRouter, Depends, HTTPException
from app.api.auth_deps import get_current_user

router = APIRouter(prefix="/account", tags=["account"])

@router.post("/delete", response_model=DeleteAccountResponse)
async def delete_account(
    request: DeleteAccountRequest,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Elimina la cuenta del usuario autenticado.
    user_id se extrae EXCLUSIVAMENTE del JWT (nunca del body).
    """
    # 1. Verificar que el email coincide
    if request.confirmation_email != current_user.email:
        raise HTTPException(status_code=422, detail="Email de confirmación no coincide.")

    # 2. Verificar confirmación textual
    if request.confirmation_text != "ELIMINAR":
        raise HTTPException(status_code=422, detail="Texto de confirmación inválido.")

    # 3. Verificar reautenticación según tipo de cuenta
    if current_user.google_id:
        # OAuth: verificar challenge token
        if not request.challenge_token:
            raise HTTPException(status_code=422, detail="Token de challenge requerido.")
        if not await verify_challenge_token(current_user.id, request.challenge_token):
            raise HTTPException(status_code=422, detail="Token expirado o inválido.")
    else:
        # Email/password: verificar contraseña actual
        if not request.current_password:
            raise HTTPException(status_code=422, detail="Contraseña actual requerida.")
        if not await verify_password(current_user, request.current_password):
            raise HTTPException(status_code=422, detail="Contraseña incorrecta.")

    # 4. Ejecutar eliminación
    await soft_delete_account(db, str(current_user.id))

    return DeleteAccountResponse()
```

Registrar el router en `app/main.py`:
```python
from app.api.v1 import account
app.include_router(account.router, prefix="/api/v1")
```

---

### PR5-009: bloquear usuarios eliminados en auth_deps

**Archivo a modificar:** `app/api/auth_deps.py`  
**Esfuerzo:** 20 min

En la función `get_current_user`, después de obtener el usuario de la DB, agregar:

```python
if user.is_deleted:
    raise HTTPException(
        status_code=403,
        detail="Esta cuenta ha sido eliminada."
    )
```

---

### PR5-010: crear frontend del dialog de eliminación

**Archivo nuevo:** `frontend/src/features/account/components/delete-account-dialog.tsx`  
**Esfuerzo:** 1.5 h

Componente modal con confirmación fuerte:

**Para cuentas email/password:**
1. Input: contraseña actual.
2. Input: escribir "ELIMINAR".
3. Input: escribir email de la cuenta.
4. Botón "Eliminar mi cuenta" (variant `destructive`).

**Para cuentas OAuth:**
1. Botón "Enviar email de confirmación" → llama a `/api/v1/account/delete/challenge`.
2. Input: token recibido por email.
3. Input: escribir "ELIMINAR".
4. Input: escribir email de la cuenta.
5. Botón "Eliminar mi cuenta".

Validación client-side:
- Botón deshabilitado hasta que los 3 campos estén completos y correctos.
- El texto "ELIMINAR" es case-sensitive.
- El email debe coincidir exactamente con `user.email`.

Al éxito: toast con key `account_delete_success`, redirect a `/login`.

---

### PR5-011: activar botón de eliminación en Profile.tsx

**Archivo a modificar:** `frontend/src/pages/Profile.tsx`  
**Esfuerzo:** 15 min

Reemplazar el placeholder deshabilitado de PR4-004 por:

```tsx
<DeleteAccountDialog
  userEmail={user.email}
  isOAuthUser={!!user.app_metadata?.provider && user.app_metadata.provider !== 'email'}
/>
```

---

### PR5-012: crear tests backend de eliminación

**Archivo nuevo:** `tests/unit/test_account_service.py`  
**Esfuerzo:** 1 h

```python
class TestAccountService:
    async def test_soft_delete_anonymizes_pii(self, db_session):
        """Verificar que email, nombre, DNI se anonimizan."""

    async def test_soft_delete_preserves_audit_events(self, db_session):
        """audit_events.principal_id mantiene referencia original."""

    async def test_soft_delete_preserves_citizen_reports(self, db_session):
        """citizen_reports persisten con reporter_user_id = NULL."""

    async def test_deleted_user_blocked_in_auth_deps(self, client):
        """GET /api/v1/profile con usuario eliminado retorna 403."""

    async def test_delete_endpoint_ignores_body_user_id(self, client):
        """Verificar que no se puede eliminar otra cuenta."""

    async def test_delete_requires_confirmation_text(self, client):
        """Falta 'ELIMINAR' → 422."""

    async def test_delete_requires_matching_email(self, client):
        """Email incorrecto → 422."""

    async def test_delete_email_user_requires_password(self, client):
        """Usuario email sin password → 422."""

    async def test_delete_oauth_user_requires_challenge(self, client):
        """Usuario OAuth sin challenge_token → 422."""
```

**Archivo nuevo:** `tests/unit/test_supabase_admin.py`  
**Esfuerzo:** 30 min

Tests con mock del cliente Supabase:
```python
class TestSupabaseAdmin:
    def test_revoke_all_sessions_calls_admin_api(self, mock_supabase):
        ...
    def test_delete_auth_user_calls_admin_api(self, mock_supabase):
        ...
    def test_missing_service_key_raises_runtime_error(self):
        ...
```

---

**Commit final PR5:** `PR5: account deletion — backend + frontend + audit + FK alignment`  
**Checklist:**
- [ ] Un usuario no puede afectar otra cuenta.
- [ ] Cuenta eliminada no puede autenticarse.
- [ ] `audit_events` tiene registro inmutable de la eliminación.
- [ ] `citizen_reports` se preservan con `reporter_user_id = NULL`.
- [ ] `user_saved_filters` y `user_investigations` se eliminan en cascada.
- [ ] Errores no exponen internals de Supabase.
- [ ] Tests backend pasan.
- [ ] Tests frontend pasan.

---

## Documentación a actualizar post-merge de todos los PRs

| Archivo | Cambio |
|---------|--------|
| `docs/frontend/README.md` | Documentar navegación responsive (breakpoints, bottom nav, drawer). Alinear badge React con versión real. |
| `docs/frontend/routing_access_ruc.md` | Agregar filas de comportamiento mobile/tablet y acciones de cuenta. |
| `docs/architecture/design/seccion_links_footer.md` | Crear: taxonomía de secciones (explorar/herramientas/cuenta/ayuda) con reglas de visibilidad. |
| `docs/INDEX.md` | Agregar referencia al documento de navegación responsive. |
| `frontend/src/pages/manual.tsx` + `translations.ts` | Actualizar contenido del manual con menú hamburguesa y acciones de perfil. |

---

## Checklist de regresión global (ejecutar al final)

**Frontend:**
- [ ] `npm run build` — cero warnings.
- [ ] `npx vitest run` — todos los tests pasan.
- [ ] `npx playwright test` — todos los specs E2E pasan.
- [ ] Viewport 390x844: bottom nav 4 slots, drawer funcional, mapa usable.
- [ ] Viewport 768x1024: topbar con hamburguesa, drawer funcional.
- [ ] Viewport 1366x768: navbar desktop sin cambios.
- [ ] Mapa: drawer sobre overlays, controles accesibles con drawer cerrado.
- [ ] Focus trap en drawer, ESC cierra, no scroll de fondo (incluir iOS Safari).
- [ ] Logout accesible desde perfil, drawer y navbar desktop.

**Backend:**
- [ ] `pytest --tb=short` — cero fallos.
- [ ] `POST /api/v1/account/delete` sin `current_password` → 422.
- [ ] `POST /api/v1/account/delete` con `user_id` en body → ignorado, usa JWT.
- [ ] Usuario eliminado → `GET /api/v1/profile` → 403.
- [ ] `audit_events` tiene registro de eliminación.

**Infraestructura:**
- [ ] `docker compose config` parsea sin errores.
- [ ] Deploy con `FRONTEND_TAG=<sha>` funciona (rollback).
- [ ] Deploy sin `FRONTEND_TAG` usa `latest` (default).
- [ ] Health check post-deploy: `/health` retorna OK.