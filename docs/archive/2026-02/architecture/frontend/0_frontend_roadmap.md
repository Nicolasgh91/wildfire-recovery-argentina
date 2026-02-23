# Roadmap técnico de integración frontend - ForestGuard

**Fecha**: 2026-02-03  
**Versión**: 1.1  
**Estado del backend**: ✅ Completo (fase 5 testing)

---

## 1. Resumen ejecutivo

Este documento define la estrategia de integración del frontend React existente con el backend FastAPI completado. El enfoque prioriza costo cero, seguridad robusta y elegancia arquitectónica.

### Decisiones clave de esta versión

| Decisión | Valor | Justificación |
|----------|-------|---------------|
| Audit logs de test | Flag `is_test: true` | Permite limpieza selectiva post-testing |
| Pasarela de pagos | Diferida a post-MVP | Costo cero, validar demanda primero |
| Email de pruebas | nicolasgabrielh91@gmail.com | Centraliza notificaciones de test |
| Testing E2E | Contra producción | Simplifica setup, datos reales |
| Seguridad VITE_* | Validada | RLS + Rate Limit + JWT protegen |

### Estado actual vs objetivo

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ESTADO ACTUAL → ESTADO OBJETIVO                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ACTUAL (Frontend)                    OBJETIVO (Integrado)                  │
│  ─────────────────                    ────────────────────                  │
│                                                                             │
│  ┌──────────────┐                     ┌──────────────┐                      │
│  │ AuthContext  │ ──── Mock ────→     │ AuthContext  │ ── Supabase JWT      │
│  │ (simulado)   │                     │ (real)       │                      │
│  └──────────────┘                     └──────────────┘                      │
│                                                                             │
│  ┌──────────────┐                     ┌──────────────┐                      │
│  │ fetch()      │ ── Disperso ──→     │ ApiService   │ ── Centralizado      │
│  │ (en componentes)                   │ (interceptores)                     │
│  └──────────────┘                     └──────────────┘                      │
│                                                                             │
│  ┌──────────────┐                     ┌──────────────┐                      │
│  │ useEffect    │ ── Manual ────→     │ TanStack     │ ── Cache + States    │
│  │ + useState   │                     │ Query        │                      │
│  └──────────────┘                     └──────────────┘                      │
│                                                                             │
│  ┌──────────────┐                     ┌──────────────┐                      │
│  │ Leaflet      │ ── Básico ────→     │ deck.gl +    │ ── H3 Heatmaps       │
│  │              │                     │ maplibre     │                      │
│  └──────────────┘                     └──────────────┘                      │
│                                                                             │
│  ┌──────────────┐                     ┌──────────────┐                      │
│  │ Stripe       │ ── Removido ──→     │ Aprobación   │ ── Admin manual      │
│  │ (pagos)      │                     │ + Créditos   │    (costo cero)      │
│  └──────────────┘                     └──────────────┘                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Seguridad de variables de entorno

Las variables con prefijo `VITE_` se exponen en el bundle del cliente. Esto es seguro cuando la arquitectura backend está correctamente configurada.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ANÁLISIS DE SEGURIDAD - VARIABLES VITE_*                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  VARIABLE                    EXPOSICIÓN    RIESGO    PROTECCIÓN             │
│  ════════════════════════════════════════════════════════════════════════   │
│                                                                             │
│  VITE_API_BASE_URL           Pública       ✅ Bajo   Rate limit por IP      │
│  VITE_SUPABASE_URL           Pública       ✅ Bajo   RLS en todas las tablas│
│  VITE_SUPABASE_ANON_KEY      Pública       ✅ Bajo   Solo acceso anónimo    │
│  VITE_MAPLIBRE_STYLE_URL     Pública       ✅ Bajo   Solo tiles estáticos   │
│                                                                             │
│  FLUJO DE PROTECCIÓN                                                        │
│  ═══════════════════                                                        │
│                                                                             │
│  Request del navegador                                                      │
│        │                                                                    │
│        ▼                                                                    │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │ Rate Limit  │───▶│ API Key     │───▶│ JWT Verify  │───▶│ RLS Check   │  │
│  │ Cloudflare  │    │ Validation  │    │ (si auth)   │    │ Supabase    │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│        │                  │                  │                  │           │
│   100 req/min        Rechaza keys      Valida sesión      Filtra filas     │
│   por IP             inválidas         y rol              por política     │
│                                                                             │
│  CONCLUSIÓN: La exposición de VITE_* es segura con la arquitectura actual.  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Usuarios de prueba

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    USUARIOS DE PRUEBA - FRONTEND E2E                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  USUARIO 1: Anónimo                                                         │
│  ══════════════════                                                         │
│  Email: N/A                                                                 │
│  Rol: anonymous                                                             │
│  Acceso: Estadísticas públicas, mapa, FAQ, home                            │
│                                                                             │
│  USUARIO 2: Usuario registrado                                              │
│  ════════════════════════════                                               │
│  Email: test.user@forestguard.ar                                            │
│  Password: ForestGuard_Test_2026!                                           │
│  Rol: user                                                                  │
│  Metadata: { "role": "user", "is_test": true }                             │
│  Acceso: Dashboard, auditoría, reportes (solicitar)                        │
│                                                                             │
│  USUARIO 3: Administrador                                                   │
│  ════════════════════════════                                               │
│  Email: test.admin@forestguard.ar                                           │
│  Password: ForestGuard_Admin_2026!                                          │
│  Rol: admin                                                                 │
│  Metadata: { "role": "admin", "is_test": true }                            │
│  Acceso: Todo + aprobar reportes + refresh imagery + créditos              │
│                                                                             │
│  EMAIL DE NOTIFICACIONES: nicolasgabrielh91@gmail.com                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Sistema de pagos (costo cero)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SISTEMA DE PAGOS - COSTO CERO MVP                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  FLUJO DE SOLICITUD DE REPORTE HD                                           │
│  ════════════════════════════════                                           │
│                                                                             │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐  │
│  │ Usuario │───▶│Solicita │───▶│ Admin   │───▶│ Aprueba │───▶│ Genera  │  │
│  │         │    │ Reporte │    │ Revisa  │    │/Rechaza │    │ PDF     │  │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘  │
│                      │                              │              │        │
│                      ▼                              ▼              ▼        │
│                Estado: pending              Estado: approved   Email con   │
│                                             o rejected         link PDF    │
│                                                                             │
│  SISTEMA DE CRÉDITOS (instituciones)                                        │
│  ═══════════════════════════════════                                        │
│                                                                             │
│  - Admin otorga N créditos a usuario institucional                         │
│  - 1 crédito = 1 imagen HD en reporte                                      │
│  - Si saldo suficiente: descuento automático                               │
│  - Si saldo insuficiente: pendiente de aprobación                          │
│                                                                             │
│  Tabla requerida: user_credits (user_id, credits, granted_by, granted_at)  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Roadmap de fases

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ROADMAP DE INTEGRACIÓN (v1.1)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  FASE 0: Fundamentos (3 días)                                               │
│  ═══════════════════════════                                                │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐                                   │
│  │ FE-0.1  │──▶│ FE-0.2  │──▶│ FE-0.3  │                                   │
│  │ApiService│  │Supabase │   │TanStack │                                   │
│  │ (1 día) │   │Auth(1d) │   │Query(1d)│                                   │
│  └─────────┘   └─────────┘   └─────────┘                                   │
│       │                            │                                        │
│       ▼                            ▼                                        │
│  FASE 1: Módulos críticos (4 días)                                          │
│  ══════════════════════════════════                                         │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐                     │
│  │ FE-1.1  │──▶│ FE-1.2  │──▶│ FE-1.3  │──▶│ FE-1.4  │                     │
│  │FireList │   │FireDetail│  │FireStats│   │ Export  │                     │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘                     │
│       │                                          │                          │
│       ▼                                          ▼                          │
│  FASE 2: Visualización geoespacial (3 días)                                 │
│  ══════════════════════════════════════════                                 │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐                                   │
│  │ FE-2.1  │──▶│ FE-2.2  │──▶│ FE-2.3  │                                   │
│  │deck.gl  │   │H3 Layer │   │MapPage  │                                   │
│  └─────────┘   └─────────┘   └─────────┘                                   │
│       │                            │                                        │
│       ▼                            ▼                                        │
│  FASE 3: Módulos premium (3 días)                                           │
│  ════════════════════════════════                                           │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐                                   │
│  │ FE-3.1  │──▶│ FE-3.2  │──▶│ FE-3.3  │                                   │
│  │ Audit   │   │ Reports │   │Contact  │                                   │
│  │ (UC-F06)│   │(UC-F11) │   │(UC-F01) │                                   │
│  └─────────┘   └─────────┘   └─────────┘                                   │
│       │                            │                                        │
│       ▼                            ▼                                        │
│  FASE 4: Pulido y testing (3 días)                                          │
│  ═════════════════════════════════                                          │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐                                   │
│  │ FE-4.1  │──▶│ FE-4.2  │──▶│ FE-4.3  │                                   │
│  │E2E Tests│   │ErrorBnd │   │Lazy Load│                                   │
│  │(prod DB)│   │+ Sentry │   │ + PWA   │                                   │
│  └─────────┘   └─────────┘   └─────────┘                                   │
│                                  │                                          │
│                                  ▼                                          │
│                          ══ INTEGRACIÓN COMPLETA ══                         │
│                                                                             │
│  Total estimado: 16 días                                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Especificaciones detalladas por tarea

### FASE 0: Fundamentos

---

#### FE-0.1: Capa de servicios API centralizada

**Objetivo**: Eliminar llamadas `fetch` dispersas y estandarizar comunicación con backend.

**Input requerido**:
- Variables de entorno: `VITE_API_BASE_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`
- Esquemas de respuesta del backend (OpenAPI)

**Proceso paso a paso**:

1. Crear estructura de directorios:
```
src/
├── services/
│   ├── api.ts              # Cliente HTTP singleton
│   ├── endpoints/
│   │   ├── fires.ts        # Endpoints de incendios
│   │   ├── audit.ts        # Endpoints de auditoría
│   │   ├── reports.ts      # Endpoints de reportes
│   │   └── contact.ts      # Endpoint de contacto
│   └── index.ts            # Barrel export
```

2. Implementar cliente HTTP con interceptores.
3. Configurar manejo global de errores.
4. Implementar retry logic para errores transitorios.

**Output esperado**:
- Archivo `src/services/api.ts` funcional
- Interceptores para JWT y API Key
- Manejo centralizado de errores HTTP

**Nombres de variables**:
```typescript
const API_BASE_URL: string
const DEFAULT_TIMEOUT: number = 30000
const MAX_RETRIES: number = 3
```

**Nombres de funciones**:
```typescript
function createApiClient(): AxiosInstance
function requestInterceptor(config: AxiosRequestConfig): AxiosRequestConfig
function responseErrorInterceptor(error: AxiosError): Promise<never>
function handleHttpError(error: AxiosError): void
```

**Dependencias**: axios@1.6.x

**Docstring obligatorio**:
```typescript
/**
 * @file api.ts
 * @description Cliente HTTP centralizado para comunicación con backend FastAPI.
 * Implementa interceptores para autenticación JWT/API-Key y manejo global de errores.
 * 
 * @requires VITE_API_BASE_URL - URL base del backend
 * @requires VITE_SUPABASE_ANON_KEY - API Key para endpoints públicos
 */
```

**Tests unitarios**:
```typescript
describe('ApiService', () => {
  it('should inject Authorization header when token exists')
  it('should inject X-API-Key header for public endpoints')
  it('should redirect to login on 401 response')
  it('should show toast on 5xx errors')
  it('should retry failed requests up to MAX_RETRIES')
})
```

---

#### FE-0.2: Integración de autenticación Supabase

**Objetivo**: Reemplazar AuthContext mock con implementación real de Supabase.

**Input requerido**:
- Credenciales Supabase: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`
- Usuarios de prueba (ver sección 3)

**Proceso paso a paso**:

1. Instalar SDK: `npm install @supabase/supabase-js`
2. Crear cliente Supabase en `src/lib/supabase.ts`
3. Refactorizar `AuthContext.tsx` para usar Supabase Auth
4. Implementar hook `useAuth()` con estados de sesión
5. Crear componente `ProtectedRoute`
6. Mapear roles de Supabase a roles de aplicación

**Output esperado**:
- `src/lib/supabase.ts`
- `src/context/AuthContext.tsx` refactorizado
- `src/hooks/useAuth.ts`
- `src/components/auth/ProtectedRoute.tsx`

**Nombres de funciones**:
```typescript
function signInWithEmail(email: string, password: string): Promise<AuthResponse>
function signOut(): Promise<void>
function getSession(): Promise<Session | null>
function onAuthStateChange(callback: (event, session) => void): Subscription
function mapSupabaseRoleToAppRole(claims: object): AppRole
```

**Dependencias**: @supabase/supabase-js@2.x

**Tests unitarios**:
```typescript
describe('AuthContext', () => {
  it('should initialize with loading state')
  it('should update user after successful login')
  it('should clear session on logout')
  it('should refresh token before expiration')
  it('should map admin role correctly')
})
```

---

#### FE-0.3: Configuración de TanStack Query

**Objetivo**: Implementar gestión de server state con cache y estados de carga robustos.

**Input requerido**:
- ApiService de FE-0.1
- Tipos TypeScript del backend

**Proceso paso a paso**:

1. Instalar: `npm install @tanstack/react-query @tanstack/react-query-devtools`
2. Configurar `QueryClient` con defaults apropiados
3. Agregar `QueryClientProvider` en `main.tsx`
4. Crear hooks base
5. Implementar invalidación de cache inteligente

**Output esperado**:
- `src/lib/queryClient.ts`
- `src/hooks/queries/useFires.ts`
- `src/hooks/queries/useFire.ts`
- `src/hooks/mutations/useAudit.ts`

**Nombres de variables**:
```typescript
const STALE_TIME: number = 5 * 60 * 1000  // 5 minutos
const CACHE_TIME: number = 30 * 60 * 1000 // 30 minutos
const queryKeys = { fires: ['fires'], fire: (id) => ['fire', id] }
```

**Nombres de funciones**:
```typescript
function useFires(filters: FireFilters): UseQueryResult<FireListResponse>
function useFire(id: string): UseQueryResult<FireDetail>
function useFireStats(filters: FireFilters): UseQueryResult<FireStats>
function useAuditMutation(): UseMutationResult<AuditResponse>
```

**Dependencias**: @tanstack/react-query@5.x, @tanstack/react-query-devtools@5.x

---

### FASE 1: Módulos críticos

---

#### FE-1.1: Migración de FireHistory a datos reales

**Objetivo**: Conectar `FireHistory.tsx` con endpoints reales usando TanStack Query.

**Proceso paso a paso**:

1. Reemplazar `useEffect` + `fetch` por `useFires()`
2. Implementar filtros sincronizados con URL params
3. Agregar skeleton loader con Tailwind animate-pulse
4. Implementar paginación server-side
5. Conectar botón de favoritos (si usuario autenticado)

**Output esperado**:
- `FireHistory.tsx` refactorizado
- `src/components/fires/FireHistorySkeleton.tsx`

**Nombres de funciones**:
```typescript
function syncFiltersWithUrl(filters: FireFilters): void
function parseUrlFilters(): FireFilters
function handleFilterChange(key: string, value: any): void
function handlePageChange(page: number): void
```

---

#### FE-1.2: Integración de FireDetail

**Objetivo**: Conectar vista de detalle con endpoint `GET /fires/{id}`.

**Proceso paso a paso**:

1. Implementar `useFire(id)` con prefetch desde lista
2. Agregar carrusel de imágenes satelitales
3. Mostrar indicadores de calidad del dato
4. Integrar botón de solicitud de imagen HD
5. Mostrar intersecciones con áreas protegidas

**Output esperado**:
- `FireDetail.tsx` refactorizado
- `src/components/fires/ImageCarousel.tsx`
- `src/components/fires/QualityIndicator.tsx`

---

#### FE-1.3: Integración de estadísticas (FireStats)

**Objetivo**: Conectar KPIs del dashboard con `GET /fires/stats`.

**Proceso paso a paso**:

1. Implementar `useFireStats()` sincronizado con filtros
2. Agregar KPIs comparativos YTD
3. Optimizar renders de gráficos con useMemo
4. Implementar lazy loading de gráficos pesados

---

#### FE-1.4: Exportación de datos

**Objetivo**: Implementar descarga de CSV con filtros aplicados.

**Proceso paso a paso**:

1. Crear mutation para export
2. Mostrar progreso para exports grandes (>1000 registros)
3. Manejar export async con polling de estado
4. Implementar notificación cuando export está listo

**Nombres de funciones**:
```typescript
function useExportMutation(): UseMutationResult<Blob>
function handleExport(filters: FireFilters): Promise<void>
function downloadBlob(blob: Blob, filename: string): void
function pollExportStatus(jobId: string): Promise<ExportStatus>
```

---

### FASE 2: Visualización geoespacial

---

#### FE-2.1: Setup de deck.gl y maplibre

**Objetivo**: Reemplazar Leaflet básico por deck.gl para visualización H3.

**Proceso paso a paso**:

1. Instalar: `npm install deck.gl @deck.gl/geo-layers @deck.gl/react maplibre-gl h3-js`
2. Crear componente base `DeckGLMap.tsx`
3. Configurar maplibre como base layer
4. Implementar controles de zoom/pan

**Output esperado**:
- `src/components/map/DeckGLMap.tsx`
- `src/components/map/MapControls.tsx`

**Nombres de variables**:
```typescript
const INITIAL_VIEW_STATE: ViewState = { longitude: -64, latitude: -34, zoom: 4 }
```

---

#### FE-2.2: H3 Heatmap Layer

**Objetivo**: Visualizar recurrencia de incendios con grilla H3.

**Proceso paso a paso**:

1. Crear hook `useRecurrenceData(bbox)`
2. Implementar H3HexagonLayer con escala de color
3. Agregar tooltip con datos de celda
4. Optimizar con viewport culling

**Output esperado**:
- `src/hooks/queries/useRecurrence.ts`
- `src/components/map/H3HeatmapLayer.tsx`

---

#### FE-2.3: Integración en MapPage

**Objetivo**: Unificar mapa con capas de incendios y recurrencia.

**Proceso paso a paso**:

1. Refactorizar `MapPage.tsx` para usar DeckGLMap
2. Agregar layer de puntos de incendios activos
3. Implementar toggle entre capas
4. Sincronizar con filtros globales

---

### FASE 3: Módulos premium

---

#### FE-3.1: Módulo de auditoría legal (UC-F06)

**Objetivo**: Implementar formulario de auditoría conectado con backend.

**Proceso paso a paso**:

1. Crear formulario con React Hook Form + Zod
2. Implementar selector de ubicación en mapa
3. Validar radio máximo (5000m hard cap)
4. Mostrar resultados con lista de incendios encontrados
5. Mostrar hash verificable del resultado
6. Implementar descarga de evidencia
7. **Agregar flag `is_test: true` en metadata para requests de prueba**

**Output esperado**:
- `src/pages/AuditPage.tsx` refactorizado
- `src/components/audit/AuditForm.tsx`
- `src/components/audit/AuditResults.tsx`
- `src/components/audit/LocationPicker.tsx`

**Validación Zod**:
```typescript
const auditSchema = z.object({
  latitude: z.number().min(-90).max(90),
  longitude: z.number().min(-180).max(180),
  radius_meters: z.number().min(100).max(5000).default(1000),
  metadata: z.object({
    is_test: z.boolean().optional()
  }).optional()
})
```

---

#### FE-3.2: Módulo de reportes (UC-F11) - Sistema de aprobación

**Objetivo**: Implementar solicitud de reportes con sistema de aprobación manual.

**Proceso paso a paso**:

1. Crear flujo de solicitud de reporte
2. Implementar selector de tipo (judicial/histórico)
3. Mostrar estimación de costo en créditos
4. Verificar saldo de créditos del usuario
5. Si saldo suficiente: descuento automático
6. Si saldo insuficiente: pendiente de aprobación
7. Implementar polling de estado del job

**Output esperado**:
- `src/pages/ReportsPage.tsx`
- `src/components/reports/ReportRequestForm.tsx`
- `src/components/reports/ReportStatus.tsx`
- `src/components/reports/CreditBalance.tsx`

**Nombres de funciones**:
```typescript
function useUserCredits(): UseQueryResult<UserCredits>
function useReportRequestMutation(): UseMutationResult<ReportJob>
function useReportStatus(jobId: string): UseQueryResult<JobStatus>
function calculateReportCost(imageCount: number): number
```

---

#### FE-3.3: Formulario de contacto (UC-F01)

**Objetivo**: Implementar formulario de contacto con validación y adjuntos.

**Proceso paso a paso**:

1. Crear formulario con validación Zod
2. Implementar upload de archivos con preview
3. Validar tipo y tamaño de adjuntos
4. Mostrar toast de confirmación

**Validación Zod**:
```typescript
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'application/pdf']

const contactSchema = z.object({
  name: z.string().min(2).max(100),
  email: z.string().email(),
  subject: z.string().min(5).max(200),
  message: z.string().min(10).max(5000),
  attachment: z.instanceof(File).optional()
    .refine(f => !f || f.size <= 5 * 1024 * 1024, 'Tamaño máximo: 5MB')
    .refine(f => !f || ALLOWED_TYPES.includes(f.type), 'Tipo no permitido')
})
```

---

### FASE 4: Pulido y testing

---

#### FE-4.1: Tests E2E con Cypress (contra producción)

**Objetivo**: Implementar tests E2E contra base de datos de producción.

**Configuración**:
```typescript
// cypress.config.ts
export default defineConfig({
  e2e: {
    baseUrl: process.env.VITE_APP_URL || 'http://localhost:5173',
    env: {
      TEST_USER_EMAIL: 'test.user@forestguard.ar',
      TEST_USER_PASSWORD: 'ForestGuard_Test_2026!',
      TEST_ADMIN_EMAIL: 'test.admin@forestguard.ar',
      TEST_ADMIN_PASSWORD: 'ForestGuard_Admin_2026!',
      IS_TEST_ENV: true
    }
  }
})
```

**Tests E2E requeridos**:
```typescript
describe('Critical Flows - Production', () => {
  it('should complete login flow with test user')
  it('should filter and paginate fire history')
  it('should view fire detail with images')
  it('should submit audit request with test flag')
  it('should request report as admin')
})
```

---

#### FE-4.2: Error Boundaries y Sentry

**Objetivo**: Implementar manejo global de errores y monitoreo.

**Output esperado**:
- `src/components/error/ErrorBoundary.tsx`
- `src/components/error/ErrorFallback.tsx`
- Sentry configurado (free tier: 5K eventos/mes)

---

#### FE-4.3: Lazy loading y PWA

**Objetivo**: Optimizar performance y habilitar PWA.

**Output esperado**:
- Code splitting por ruta
- Manifest PWA funcional
- Cache de assets estáticos

---

## 7. Preguntas de validación por caso de uso

### UC-F01: Contacto y soporte

| # | Pregunta | Respuesta |
|---|----------|-----------|
| 1 | ¿Tipos de adjuntos? | .jpg, .jpeg, .png, .pdf |
| 2 | ¿Límite de tamaño? | 5MB máximo |
| 3 | ¿Se persisten archivos? | No, solo email |
| 4 | ¿Feedback al usuario? | Toast 202 Accepted |
| 5 | ¿Email de tests? | nicolasgabrielh91@gmail.com |

### UC-F03: Dashboard histórico

| # | Pregunta | Respuesta |
|---|----------|-----------|
| 1 | ¿page_size máximo? | 100 (hard limit) |
| 2 | ¿Búsqueda de texto? | ILIKE |
| 3 | ¿Export >1000? | Async con polling |
| 4 | ¿KPIs comparativos? | Sí, YTD |
| 5 | ¿Loading state? | Skeleton animate-pulse |

### UC-F06: Auditoría legal

| # | Pregunta | Respuesta |
|---|----------|-----------|
| 1 | ¿Radio máximo? | 5000m |
| 2 | ¿Cuántos incendios? | TODOS en radio |
| 3 | ¿Thumbnails? | Siempre, HD bajo demanda |
| 4 | ¿Audit log editable? | No, append-only |
| 5 | ¿Registros de test? | Flag `is_test: true` |

### UC-F11: Reportes especializados

| # | Pregunta | Respuesta |
|---|----------|-----------|
| 1 | ¿Cómo se paga? | Créditos + aprobación admin |
| 2 | ¿Máx imágenes? | 12 fijo |
| 3 | ¿Idioma? | Solo español |
| 4 | ¿Cadena custodia? | Obligatoria |
| 5 | ¿Sin créditos? | Pendiente aprobación |

---

## 8. Dependencias npm

```bash
# Fase 0
npm install @supabase/supabase-js @tanstack/react-query @tanstack/react-query-devtools axios

# Fase 2
npm install deck.gl @deck.gl/geo-layers @deck.gl/react maplibre-gl h3-js

# Fase 4
npm install -D cypress @testing-library/cypress
npm install @sentry/react
```

---

## 9. Variables de entorno

```env
# Backend
VITE_API_BASE_URL=https://api.forestguard.ar/api/v1

# Supabase
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...

# Mapas
VITE_MAPLIBRE_STYLE_URL=https://tiles.forestguard.ar/style.json

# Monitoreo
VITE_SENTRY_DSN=https://xxx@sentry.io/xxx
```

---

## 10. Script de limpieza post-testing

```sql
-- Eliminar audit logs de test
DELETE FROM audit_logs WHERE metadata->>'is_test' = 'true';

-- Verificar limpieza
SELECT COUNT(*) FROM audit_logs WHERE metadata->>'is_test' = 'true';
```

---

## 11. Checklist de entrega

### Fase 0
- [x] `src/services/api.ts`
- [x] `src/lib/supabase.ts`
- [x] `src/context/AuthContext.tsx`
- [x] `src/lib/queryClient.ts`
- [ ] Usuarios de prueba creados

### Fase 1
- [x] `FireHistory.tsx` refactorizado
- [x] `FireDetail.tsx` con carrusel
- [x] Stats sincronizados
- [x] Export CSV funcional

### Fase 2
- [x] Mapa Leaflet (reemplaza deck.gl)
- [x] H3 heatmap (Leaflet)
- [ ] Toggle de capas

### Fase 3
- [x] Auditoría con flag is_test
- [x] Reportes con créditos
- [x] Formulario contacto

### Fase 4
- [x] Tests E2E
- [x] Error boundaries
- [x] Sentry
- [ ] PWA

## 12. Cambios fuera del plan (implementados)
- Reemplazo de deck.gl/maplibre por Leaflet + leaflet.glify, documentado en `docs/architecture/frontend/frontend_map_01_leaflet_migration.md`.
- Popup de hotspots mantiene acceso a detalle de incendio y cruce con áreas protegidas.
- Compra de créditos simplificada (input + botón MercadoPago) y nueva pantalla Perfil con créditos.
- Modo mock de MercadoPago para pruebas locales (MP_MOCK_MODE/MP_MOCK_APPROVE) y endpoint `/payments/pricing` para precios en ARS.
- Backend acepta JWT de Supabase o X-API-Key en endpoints públicos; normalización de secretos en auth.

---

**Estimación total**: 16 días  
**Prioridad**: Fase 0 → Fase 1 → Fase 3 → Fase 2 → Fase 4
