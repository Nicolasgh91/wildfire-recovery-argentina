# Tareas técnicas frontend - ForestGuard

**Proyecto**: ForestGuard  
**Documento**: Especificaciones para agente de código  
**Versión**: 1.2  
**Fecha**: 2026-02-03  
**Estimación total**: 18 días

---

### Estructura del documento

ESTRUCTURA DEL DOCUMENTO
════════════════════════

FASE 0: Fundamentos (3 tareas)
├── FE-0.1: api.ts completo con interceptores
├── FE-0.2: AuthContext + ProtectedRoute + supabase.ts
└── FE-0.3: queryClient.ts + hooks useFires, useFire

FASE 1: Módulos críticos (4 tareas)
├── FE-1.1: FireHistory refactorizado + Skeleton
├── FE-1.2: FireDetail + QualityIndicator
├── FE-1.3: useFireStats
└── FE-1.4: useExportMutation

FASE 2: Visualización (3 tareas)
├── FE-2.1: DeckGLMap.tsx
├── FE-2.2: useH3Layer hook
└── FE-2.3: MapPage integrado

FASE 3: Premium (4 tareas)
├── FE-3.1: AuditPage + useAuditMutation
├── FE-3.2: Reportes con créditos
├── FE-3.3: ContactForm con Zod
└── FE-3.4: MercadoPago (ver documento separado)

FASE 4: Testing (3 tareas)
├── FE-4.1: Cypress config + tests críticos
├── FE-4.2: ErrorBoundary + Sentry
└── FE-4.3: App.tsx con lazy loading






## Índice de tareas

| Fase | ID | Tarea | Estimación |
|------|-----|-------|------------|
| 0 | FE-0.1 | Capa de servicios API centralizada | 1 día |
| 0 | FE-0.2 | Integración autenticación Supabase | 1 día |
| 0 | FE-0.3 | Configuración TanStack Query | 1 día |
| 1 | FE-1.1 | Migración FireHistory a datos reales | 1 día |
| 1 | FE-1.2 | Integración FireDetail | 1 día |
| 1 | FE-1.3 | Integración FireStats | 1 día |
| 1 | FE-1.4 | Exportación de datos CSV | 1 día |
| 2 | FE-2.1 | Setup deck.gl y maplibre | 1 día |
| 2 | FE-2.2 | H3 Heatmap Layer | 1 día |
| 2 | FE-2.3 | Integración MapPage | 1 día |
| 3 | FE-3.1 | Módulo de auditoría legal | 1 día |
| 3 | FE-3.2 | Módulo de reportes | 1 día |
| 3 | FE-3.3 | Formulario de contacto | 1 día |
| 3 | FE-3.4 | Integración MercadoPago | 2 días |
| 4 | FE-4.1 | Tests E2E con Cypress | 1 día |
| 4 | FE-4.2 | Error Boundaries y Sentry | 1 día |
| 4 | FE-4.3 | Lazy loading y PWA | 1 día |

---

# FASE 0: Fundamentos

---

## FE-0.1: Capa de servicios API centralizada

### Objetivo
Eliminar llamadas `fetch` dispersas en componentes y crear un cliente HTTP centralizado con interceptores para autenticación y manejo de errores.

### Input requerido
- Variables de entorno: `VITE_API_BASE_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`
- Documentación OpenAPI del backend

### Proceso paso a paso

1. Instalar axios: `npm install axios`
2. Crear estructura:
```
src/services/
├── api.ts
├── endpoints/
│   ├── fires.ts
│   ├── audit.ts
│   ├── reports.ts
│   ├── contact.ts
│   └── index.ts
└── index.ts
```
3. Implementar interceptores
4. Crear endpoints por módulo

### Output esperado
- `src/services/api.ts` - Cliente HTTP
- `src/services/endpoints/*.ts` - Endpoints organizados

### Variables y funciones

```typescript
// Variables
const API_BASE_URL: string
const DEFAULT_TIMEOUT: number = 30000
const MAX_RETRIES: number = 3

// Funciones
function createApiClient(): AxiosInstance
function requestInterceptor(config): config
function responseErrorInterceptor(error): Promise<never>
function getAuthToken(): string | null
```

### Código: src/services/api.ts

```typescript
/**
 * @file api.ts
 * @description Cliente HTTP centralizado con interceptores JWT/API-Key.
 */

import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import { toast } from 'sonner';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY;
const DEFAULT_TIMEOUT = 30000;
const MAX_RETRIES = 3;
const RETRYABLE_STATUS_CODES = [408, 429, 500, 502, 503, 504];

function getAuthToken(): string | null {
  try {
    const url = new URL(import.meta.env.VITE_SUPABASE_URL);
    const storageKey = `sb-${url.hostname.split('.')[0]}-auth-token`;
    const sessionStr = localStorage.getItem(storageKey);
    if (!sessionStr) return null;
    return JSON.parse(sessionStr)?.access_token || null;
  } catch {
    return null;
  }
}

function requestInterceptor(config: InternalAxiosRequestConfig) {
  config.headers['X-API-Key'] = SUPABASE_ANON_KEY;
  const token = getAuthToken();
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  return config;
}

async function responseErrorInterceptor(error: AxiosError) {
  const config = error.config as InternalAxiosRequestConfig & { _retryCount?: number };
  
  if (config && (config._retryCount || 0) < MAX_RETRIES) {
    if (!error.response || RETRYABLE_STATUS_CODES.includes(error.response.status)) {
      config._retryCount = (config._retryCount || 0) + 1;
      await new Promise(r => setTimeout(r, 1000 * config._retryCount!));
      return apiClient.request(config);
    }
  }
  
  handleHttpError(error);
  return Promise.reject(error);
}

function handleHttpError(error: AxiosError) {
  const status = error.response?.status;
  switch (status) {
    case 401:
      toast.error('Sesión expirada');
      window.location.href = '/login';
      break;
    case 403:
      toast.error('Acceso denegado');
      break;
    case 422:
      toast.error('Datos inválidos');
      break;
    case 429:
      toast.error('Demasiadas solicitudes');
      break;
    default:
      if (status && status >= 500) {
        toast.error('Error del servidor');
      } else if (!error.response) {
        toast.error('Error de conexión');
      }
  }
}

function createApiClient(): AxiosInstance {
  const client = axios.create({
    baseURL: API_BASE_URL,
    timeout: DEFAULT_TIMEOUT,
    headers: { 'Content-Type': 'application/json' },
  });
  client.interceptors.request.use(requestInterceptor);
  client.interceptors.response.use(r => r, responseErrorInterceptor);
  return client;
}

export const apiClient = createApiClient();
```

### Código: src/services/endpoints/fires.ts

```typescript
/**
 * @file fires.ts
 * @description Endpoints de incendios forestales.
 */

import { apiClient } from '../api';
import type { FireListResponse, FireDetailResponse, FireStatsResponse, FireFilters } from '@/types/fire';

export async function getFires(filters?: FireFilters): Promise<FireListResponse> {
  const response = await apiClient.get<FireListResponse>('/fires', { params: filters });
  return response.data;
}

export async function getFireById(id: string): Promise<FireDetailResponse> {
  const response = await apiClient.get<FireDetailResponse>(`/fires/${id}`);
  return response.data;
}

export async function getFireStats(filters?: FireFilters): Promise<FireStatsResponse> {
  const response = await apiClient.get<FireStatsResponse>('/fires/stats', { params: filters });
  return response.data;
}

export async function exportFires(filters?: FireFilters): Promise<Blob> {
  const response = await apiClient.get('/fires/export', { params: filters, responseType: 'blob' });
  return response.data;
}
```

### Tests unitarios

```typescript
describe('ApiService', () => {
  it('should inject X-API-Key header')
  it('should inject Authorization when token exists')
  it('should retry on 5xx errors')
  it('should redirect to login on 401')
  it('should handle network timeout')
})
```

---

## FE-0.2: Integración autenticación Supabase

### Objetivo
Reemplazar AuthContext mock con Supabase Auth real.

### Input requerido
- Variables: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`
- Usuarios de prueba creados

### Proceso paso a paso

1. Instalar: `npm install @supabase/supabase-js`
2. Crear `src/lib/supabase.ts`
3. Refactorizar `src/context/AuthContext.tsx`
4. Crear `src/components/auth/ProtectedRoute.tsx`

### Output esperado
- Cliente Supabase configurado
- AuthContext con login/logout real
- ProtectedRoute para rutas privadas

### Código: src/lib/supabase.ts

```typescript
/**
 * @file supabase.ts
 * @description Cliente Supabase singleton.
 */

import { createClient } from '@supabase/supabase-js';

export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY,
  {
    auth: {
      autoRefreshToken: true,
      persistSession: true,
    },
  }
);
```

### Código: src/context/AuthContext.tsx

```typescript
/**
 * @file AuthContext.tsx
 * @description Contexto de autenticación con Supabase.
 */

import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react';
import type { User, Session } from '@supabase/supabase-js';
import { supabase } from '@/lib/supabase';

type UserRole = 'admin' | 'user' | 'anonymous';
type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated';

interface AuthState {
  user: User | null;
  session: Session | null;
  status: AuthStatus;
  role: UserRole;
}

interface AuthContextValue extends AuthState {
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function mapRole(user: User | null): UserRole {
  if (!user) return 'anonymous';
  return user.app_metadata?.role === 'admin' ? 'admin' : 'user';
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    session: null,
    status: 'loading',
    role: 'anonymous',
  });

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setState({
        user: session?.user ?? null,
        session,
        status: session ? 'authenticated' : 'unauthenticated',
        role: mapRole(session?.user ?? null),
      });
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_, session) => {
      setState({
        user: session?.user ?? null,
        session,
        status: session ? 'authenticated' : 'unauthenticated',
        role: mapRole(session?.user ?? null),
      });
    });

    return () => subscription.unsubscribe();
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw error;
  }, []);

  const signOut = useCallback(async () => {
    await supabase.auth.signOut();
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
}
```

### Código: src/components/auth/ProtectedRoute.tsx

```typescript
/**
 * @file ProtectedRoute.tsx
 * @description Guard de rutas protegidas.
 */

import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { Loader2 } from 'lucide-react';

interface Props {
  children: React.ReactNode;
  requiredRole?: 'admin' | 'user';
}

export function ProtectedRoute({ children, requiredRole }: Props) {
  const { status, role } = useAuth();
  const location = useLocation();

  if (status === 'loading') {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  if (status === 'unauthenticated') {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requiredRole && role !== requiredRole && role !== 'admin') {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
```

---

## FE-0.3: Configuración TanStack Query

### Objetivo
Implementar gestión de server state con cache inteligente.

### Proceso paso a paso

1. Instalar: `npm install @tanstack/react-query @tanstack/react-query-devtools`
2. Crear `src/lib/queryClient.ts`
3. Crear hooks en `src/hooks/queries/`
4. Agregar provider en `main.tsx`

### Código: src/lib/queryClient.ts

```typescript
/**
 * @file queryClient.ts
 * @description Configuración de TanStack Query.
 */

import { QueryClient } from '@tanstack/react-query';

export const QUERY_CONFIG = {
  STALE_TIME: 5 * 60 * 1000,
  GC_TIME: 30 * 60 * 1000,
};

export const queryKeys = {
  fires: {
    all: ['fires'],
    list: (filters: object) => ['fires', 'list', filters],
    detail: (id: string) => ['fires', 'detail', id],
    stats: (filters: object) => ['fires', 'stats', filters],
  },
  audit: {
    result: (id: string) => ['audit', id],
  },
  credits: {
    balance: () => ['credits', 'balance'],
    transactions: (page: number) => ['credits', 'transactions', page],
  },
  payments: {
    status: (id: string) => ['payments', id],
  },
};

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: QUERY_CONFIG.STALE_TIME,
      gcTime: QUERY_CONFIG.GC_TIME,
      retry: 3,
      refetchOnWindowFocus: true,
    },
  },
});
```

### Código: src/hooks/queries/useFires.ts

```typescript
/**
 * @file useFires.ts
 * @description Hook para lista de incendios.
 */

import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { getFires } from '@/services/endpoints/fires';
import { queryKeys } from '@/lib/queryClient';
import type { FireFilters } from '@/types/fire';

export function useFires(filters?: FireFilters) {
  return useQuery({
    queryKey: queryKeys.fires.list(filters || {}),
    queryFn: () => getFires(filters),
    placeholderData: keepPreviousData,
  });
}
```

### Código: src/hooks/queries/useFire.ts

```typescript
/**
 * @file useFire.ts
 * @description Hook para detalle de incendio.
 */

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getFireById } from '@/services/endpoints/fires';
import { queryKeys, QUERY_CONFIG } from '@/lib/queryClient';

export function useFire(id: string) {
  return useQuery({
    queryKey: queryKeys.fires.detail(id),
    queryFn: () => getFireById(id),
    enabled: !!id,
  });
}

export function usePrefetchFire() {
  const queryClient = useQueryClient();
  return (id: string) => {
    queryClient.prefetchQuery({
      queryKey: queryKeys.fires.detail(id),
      queryFn: () => getFireById(id),
      staleTime: QUERY_CONFIG.STALE_TIME,
    });
  };
}
```

---

# FASE 1: Módulos críticos

---

## FE-1.1: Migración FireHistory

### Objetivo
Refactorizar FireHistory para usar TanStack Query.

### Código: src/components/fires/FireHistorySkeleton.tsx

```typescript
/**
 * @file FireHistorySkeleton.tsx
 * @description Skeleton loader con Tailwind animate-pulse.
 */

export function FireHistorySkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex justify-between">
        <div className="h-8 w-48 bg-gray-200 rounded animate-pulse" />
        <div className="h-10 w-32 bg-gray-200 rounded animate-pulse" />
      </div>
      <div className="grid grid-cols-6 gap-4">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="bg-white p-4 rounded-lg">
            <div className="h-4 w-24 bg-gray-200 rounded animate-pulse mb-2" />
            <div className="h-8 w-16 bg-gray-200 rounded animate-pulse" />
          </div>
        ))}
      </div>
      <div className="bg-white rounded-lg">
        {[...Array(10)].map((_, i) => (
          <div key={i} className="border-b p-4 flex gap-4">
            <div className="h-4 w-24 bg-gray-200 rounded animate-pulse" />
            <div className="h-4 w-32 bg-gray-200 rounded animate-pulse" />
            <div className="h-4 w-20 bg-gray-200 rounded animate-pulse" />
          </div>
        ))}
      </div>
    </div>
  );
}
```

### Código: src/pages/FireHistory.tsx (refactorizado)

```typescript
/**
 * @file FireHistory.tsx
 * @description Página de historial con TanStack Query y URL sync.
 */

import { useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useFires, usePrefetchFire } from '@/hooks/queries/useFires';
import { useFireStats } from '@/hooks/queries/useFireStats';
import { FireHistorySkeleton } from '@/components/fires/FireHistorySkeleton';
import { Button } from '@/components/ui/button';
import { Download } from 'lucide-react';

export default function FireHistory() {
  const [searchParams, setSearchParams] = useSearchParams();
  const prefetchFire = usePrefetchFire();

  const filters = useMemo(() => ({
    page: parseInt(searchParams.get('page') || '1'),
    page_size: parseInt(searchParams.get('page_size') || '20'),
    province: searchParams.get('province') || undefined,
    status: searchParams.get('status') || undefined,
    search: searchParams.get('search') || undefined,
  }), [searchParams]);

  const { data, isLoading, error } = useFires(filters);
  const { data: stats } = useFireStats(filters);

  const handleFilterChange = useCallback((key: string, value: string | undefined) => {
    setSearchParams(prev => {
      const params = new URLSearchParams(prev);
      if (value) params.set(key, value);
      else params.delete(key);
      if (key !== 'page') params.set('page', '1');
      return params;
    });
  }, [setSearchParams]);

  if (isLoading && !data) return <FireHistorySkeleton />;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Histórico de incendios</h1>
        <Button variant="outline">
          <Download className="h-4 w-4 mr-2" />
          Exportar CSV
        </Button>
      </div>
      {/* Stats, Filters, Table, Pagination components here */}
    </div>
  );
}
```

---

## FE-1.2 a FE-1.4: Resumen

| Tarea | Output principal |
|-------|------------------|
| FE-1.2 | FireDetail.tsx con useFire(), carrusel, QualityIndicator |
| FE-1.3 | useFireStats() sincronizado con filtros |
| FE-1.4 | useExportMutation() con descarga de blob |

---

# FASE 2: Visualización geoespacial

---

## FE-2.1: Setup deck.gl

### Instalar

```bash
npm install deck.gl @deck.gl/geo-layers @deck.gl/react maplibre-gl h3-js
```

### Código: src/components/map/DeckGLMap.tsx

```typescript
/**
 * @file DeckGLMap.tsx
 * @description Mapa base con deck.gl y maplibre.
 */

import { useState, useCallback } from 'react';
import { Map } from 'react-map-gl/maplibre';
import DeckGL from '@deck.gl/react';
import type { MapViewState, Layer } from '@deck.gl/core';
import 'maplibre-gl/dist/maplibre-gl.css';

const INITIAL_VIEW: MapViewState = {
  longitude: -64,
  latitude: -34,
  zoom: 4,
  pitch: 0,
  bearing: 0,
};

interface Props {
  layers?: Layer[];
  onViewStateChange?: (vs: MapViewState) => void;
  onClick?: (info: any) => void;
}

export function DeckGLMap({ layers = [], onViewStateChange, onClick }: Props) {
  const [viewState, setViewState] = useState(INITIAL_VIEW);

  const handleChange = useCallback(({ viewState: vs }) => {
    setViewState(vs);
    onViewStateChange?.(vs);
  }, [onViewStateChange]);

  return (
    <DeckGL
      viewState={viewState}
      onViewStateChange={handleChange}
      controller
      layers={layers}
      onClick={onClick}
    >
      <Map mapStyle="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json" />
    </DeckGL>
  );
}
```

---

## FE-2.2: H3 Heatmap

### Código: src/components/map/useH3Layer.ts

```typescript
/**
 * @file useH3Layer.ts
 * @description Hook para crear capa H3 de recurrencia.
 */

import { useMemo } from 'react';
import { H3HexagonLayer } from '@deck.gl/geo-layers';

interface H3Cell {
  h3Index: string;
  intensity: number;
}

export function useH3Layer(data: H3Cell[], visible = true) {
  return useMemo(() => {
    if (!visible || !data.length) return null;
    
    const max = Math.max(...data.map(d => d.intensity));
    
    return new H3HexagonLayer({
      id: 'h3-heatmap',
      data,
      pickable: true,
      filled: true,
      extruded: false,
      opacity: 0.6,
      getHexagon: d => d.h3Index,
      getFillColor: d => {
        const n = d.intensity / max;
        return n < 0.5 
          ? [0, 255 * n * 2, 0, 180]
          : [255 * (n - 0.5) * 2, 255 * (1 - (n - 0.5) * 2), 0, 180];
      },
    });
  }, [data, visible]);
}
```

---

# FASE 3: Módulos premium

---

## FE-3.1: Auditoría legal

### Código: src/hooks/mutations/useAudit.ts

```typescript
/**
 * @file useAudit.ts
 * @description Mutation para auditoría de uso del suelo.
 */

import { useMutation } from '@tanstack/react-query';
import { performAudit } from '@/services/endpoints/audit';

export function useAuditMutation() {
  return useMutation({
    mutationFn: performAudit,
  });
}
```

### Código: src/pages/AuditPage.tsx

```typescript
/**
 * @file AuditPage.tsx
 * @description Formulario de auditoría legal.
 */

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useAuditMutation } from '@/hooks/mutations/useAudit';

const schema = z.object({
  latitude: z.number().min(-90).max(90),
  longitude: z.number().min(-180).max(180),
  radius_meters: z.number().min(100).max(5000).default(1000),
});

export default function AuditPage() {
  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(schema),
  });
  
  const { mutate, isPending, data } = useAuditMutation();
  
  const onSubmit = (values) => {
    mutate({
      ...values,
      metadata: { is_test: import.meta.env.MODE === 'test' }
    });
  };
  
  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      {/* Form fields */}
    </form>
  );
}
```

---

## FE-3.2: Reportes

Ver sistema de créditos y aprobación en roadmap principal.

---

## FE-3.3: Contacto

### Código: src/components/contact/ContactForm.tsx

```typescript
/**
 * @file ContactForm.tsx
 * @description Formulario de contacto con adjuntos.
 */

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation } from '@tanstack/react-query';
import { sendContactForm } from '@/services/endpoints/contact';
import { toast } from 'sonner';

const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'application/pdf'];

const schema = z.object({
  name: z.string().min(2).max(100),
  email: z.string().email(),
  subject: z.string().min(5).max(200),
  message: z.string().min(10).max(5000),
  attachment: z.instanceof(File).optional()
    .refine(f => !f || f.size <= 5 * 1024 * 1024, 'Máximo 5MB')
    .refine(f => !f || ALLOWED_TYPES.includes(f.type), 'Tipo no permitido'),
});

export function ContactForm() {
  const form = useForm({ resolver: zodResolver(schema) });
  
  const { mutate, isPending } = useMutation({
    mutationFn: sendContactForm,
    onSuccess: () => toast.success('Mensaje enviado'),
  });
  
  return (
    <form onSubmit={form.handleSubmit(data => mutate(data))}>
      {/* Fields */}
    </form>
  );
}
```

---

## FE-3.4: MercadoPago

**Ver documento separado**: `mercadopago_technical_tasks.md`

Incluye:
- Hooks: useCreateCheckout, usePaymentStatus, useCreditBalance
- Componentes: PaymentButton, PaymentStatusPoller, CreditBalance
- Página: PaymentReturnPage

---

# FASE 4: Pulido y testing

---

## FE-4.1: Tests E2E Cypress

### Configuración

```typescript
// cypress.config.ts
export default defineConfig({
  e2e: {
    baseUrl: 'http://localhost:5173',
    env: {
      TEST_USER_EMAIL: 'test.user@forestguard.ar',
      TEST_USER_PASSWORD: 'ForestGuard_Test_2026!',
    },
  },
});
```

### Tests críticos

```typescript
// cypress/e2e/critical.cy.ts

describe('Critical Flows', () => {
  it('login flow', () => {
    cy.visit('/login');
    cy.get('[data-testid=email]').type(Cypress.env('TEST_USER_EMAIL'));
    cy.get('[data-testid=password]').type(Cypress.env('TEST_USER_PASSWORD'));
    cy.get('[data-testid=submit]').click();
    cy.url().should('not.include', '/login');
  });

  it('filter and paginate fires', () => {
    cy.visit('/fires/history');
    cy.get('[data-testid=province-filter]').select('Córdoba');
    cy.url().should('include', 'province=Córdoba');
  });

  it('submit audit', () => {
    cy.visit('/audit');
    cy.get('[data-testid=latitude]').type('-31.4');
    cy.get('[data-testid=longitude]').type('-64.2');
    cy.get('[data-testid=submit]').click();
    cy.get('[data-testid=audit-result]').should('be.visible');
  });
});
```

---

## FE-4.2: Error Boundaries

### Código: src/components/error/ErrorBoundary.tsx

```typescript
/**
 * @file ErrorBoundary.tsx
 * @description Manejo global de errores con Sentry.
 */

import { Component, ReactNode } from 'react';
import * as Sentry from '@sentry/react';

interface Props { children: ReactNode }
interface State { hasError: boolean; error?: Error }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    Sentry.captureException(error, { extra: { info } });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="text-center py-12">
          <h1>Algo salió mal</h1>
          <button onClick={() => this.setState({ hasError: false })}>
            Reintentar
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
```

---

## FE-4.3: Lazy loading

### Código: src/App.tsx

```typescript
/**
 * @file App.tsx
 * @description Routes con lazy loading.
 */

import { Suspense, lazy } from 'react';
import { Routes, Route } from 'react-router-dom';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';

const Home = lazy(() => import('@/pages/Home'));
const FireHistory = lazy(() => import('@/pages/FireHistory'));
const FireDetail = lazy(() => import('@/pages/FireDetail'));
const MapPage = lazy(() => import('@/pages/MapPage'));
const AuditPage = lazy(() => import('@/pages/AuditPage'));
const LoginPage = lazy(() => import('@/pages/LoginPage'));

export default function App() {
  return (
    <Suspense fallback={<div>Cargando...</div>}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/map" element={<MapPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/fires/history" element={
          <ProtectedRoute><FireHistory /></ProtectedRoute>
        } />
        <Route path="/fires/:id" element={
          <ProtectedRoute><FireDetail /></ProtectedRoute>
        } />
        <Route path="/audit" element={
          <ProtectedRoute><AuditPage /></ProtectedRoute>
        } />
      </Routes>
    </Suspense>
  );
}
```

---

# Checklist final

## Fase 0
- [x] src/services/api.ts
- [x] src/lib/supabase.ts
- [x] src/context/AuthContext.tsx
- [x] src/lib/queryClient.ts

## Fase 1
- [x] FireHistory refactorizado
- [x] FireDetail con carrusel
- [x] FireStats conectado
- [x] Export CSV

## Fase 2
- [x] Leaflet MapView (reemplaza DeckGLMap.tsx)
- [x] H3 heatmap layer (leaflet.glify)
- [x] MapPage integrado

## Fase 3
- [x] Auditoría con is_test flag
- [x] Reportes con créditos
- [x] Contacto con adjuntos
- [x] MercadoPago

## Fase 4
- [x] Tests Cypress
- [x] Error boundaries
- [x] Lazy loading

## Cambios fuera del plan (implementados)
- Migración de mapa a Leaflet con plan propio (`frontend_map_01_leaflet_migration.md`) en lugar de deck.gl/maplibre.
- UI de compra de créditos simplificada (input + botón MercadoPago) y pantalla de perfil con créditos.
- Modo mock de MercadoPago para pruebas locales (MP_MOCK_MODE/MP_MOCK_APPROVE).

---

**Total**: 18 días | **Archivos**: ~50 | **Dependencias nuevas**: 12
