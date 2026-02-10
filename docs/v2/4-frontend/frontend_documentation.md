# ForestGuard - Frontend Documentation v2.0

**Fecha de actualización**: Febrero 2026  
**Framework**: React 18  
**Build Tool**: Vite 5  
**Language**: TypeScript 5  
**Estado**: 85% implementado (20 páginas activas)

---

## 1. Visión General del Frontend

El frontend de ForestGuard es una **Single Page Application (SPA)** construida con React 18, Vite y TypeScript que proporciona:

1. **Interfaz pública** para consulta de incendios y estadísticas
2. **Dashboard autenticado** con análisis y reportes premium
3. **Wizard de exploración satelital** (UC-F11)
4. **Sistema de auditoría legal** (UC-F06)
5. **Mapas interactivos** con Leaflet + H3 heatmaps
6. **Multi-idioma** (Español/Inglés) con i18n

### Principios de Diseño

- **Performance-First**: Code splitting, lazy loading, optimistic UI
- **Mobile-First**: Responsive desde 320px
- **Accessibility**: WCAG 2.1 AA compliance
- **Type Safety**: TypeScript strict mode
- **Component Isolation**: 93 componentes reutilizables
- **Declarative**: React hooks + Context API (no Redux)

---

## 2. Estructura del Proyecto

```
frontend/src/
├── main.tsx                # Entry point + providers
├── App.tsx                 # Router + lazy loading
├── pages/                  # 20 page components
│   ├── Home.tsx            # Landing page
│   ├── Login.tsx           # Auth page (Google OAuth + Email)
│   ├── Register.tsx        # Registration page
│   ├── MapPage.tsx         # Mapa interactivo M1/V1
│   ├── FireHistory.tsx     # Dashboard UC-F03 (49KB)
│   ├── FireDetail.tsx      # Detalle de incendio
│   ├── Audit.tsx           # Auditoría legal UC-F06 (24KB)
│   ├── Exploration.tsx     # Wizard exploración UC-F11 (51KB)
│   ├── Certificates.tsx    # Certificados UC-F10
│   ├── Profile.tsx         # Perfil de usuario
│   ├── Credits.tsx         # Compra de créditos
│   ├── PaymentReturnPage.tsx
│   ├── CitizenReport.tsx   # Reportes ciudadanos UC-09
│   ├── Shelters.tsx        # Refugios UC-04
│   ├── contact.tsx         # Formulario contacto UC-F01
│   ├── faq.tsx             # Preguntas frecuentes
│   ├── manual.tsx          # Manual de usuario
│   ├── glossary.tsx        # Glosario de términos
│   ├── NotFound.tsx        # 404 page
│   └── ...
├── components/             # 93 reusable components
│   ├── ui/                 # shadcn/ui components (43)
│   │   ├── button.tsx
│   │   ├── input.tsx
│   │   ├── card.tsx
│   │   ├── dialog.tsx
│   │   ├── select.tsx
│   │   └── ...
│   ├── auth/               # Authentication (3)
│   │   ├── ProtectedRoute.tsx
│   │   ├── LoginForm.tsx
│   │   └── RegisterForm.tsx
│   ├── layout/             # Layout components (5)
│   │   ├── Navbar.tsx
│   │   ├── Footer.tsx
│   │   ├── Sidebar.tsx
│   │   └── AppShell.tsx
│   ├── map/                # Map components (12)
│   │   ├── LeafletMap.tsx
│   │   ├── H3HeatmapLayer.tsx
│   │   ├── FireMarker.tsx
│   │   ├── ProtectedAreaLayer.tsx
│   │   └── ...
│   ├── dashboard/          # Dashboard widgets (15)
│   │   ├── FireStatsCard.tsx
│   │   ├── RecurrenceChart.tsx
│   │   ├── ProvinceTable.tsx
│   │   └── ...
│   └── exploration/        # Exploration wizard (8)
│       ├── StepSelector.tsx
│       ├── ImagePreview.tsx
│       ├── TimelineSlider.tsx
│       └── ...
├── services/               # API clients (14)
│   ├── api.ts              # Axios instance + interceptors
│   ├── fireService.ts
│   ├── auditService.ts
│   ├── explorationService.ts
│   ├── authService.ts
│   ├── paymentService.ts
│   └── ...
├── hooks/                  # Custom hooks (17)
│   ├── useAuth.ts
│   ├── useLanguage.ts
│   ├── useFires.ts
│   ├── useDebounce.ts
│   ├── useIntersectionObserver.ts
│   └── ...
├── context/                # React Context (2)
│   ├── AuthContext.tsx
│   └── LanguageContext.tsx
├── types/                  # TypeScript definitions (12)
│   ├── fire.ts
│   ├── user.ts
│   ├── audit.ts
│   └── ...
├── lib/                    # Utilities
│   ├── utils.ts            # cn() helper
│   ├── constants.ts
│   └── validators.ts
└── __tests__/              # Tests
    ├── unit/
    ├── integration/
    └── e2e/
```

---

## 3. Routing (React Router v6)

### 3.1 Route Table

**Total**: 20 rutas activas

| Ruta | Componente | Auth | Lazy | Descripción |
|------|-----------|------|------|-------------|
| `/` | `Home` | ❌ | ✅ | Landing page + login |
| `/login` | `Login` | ❌ | ✅ | Página de login (redirige si auth) |
| `/register` | `Register` | ❌ | ✅ | Registro de usuario |
| `/map` | `MapPage` | ❌ | ✅ | Mapa interactivo M1/V1 |
| `/fires` | `FireHistory` | ✅ | ✅ | Dashboard UC-F03 |
| `/fires/:id` | `FireDetail` | ✅ | ✅ | Detalle de incendio específico |
| `/audit` | `Audit` | ✅ | ✅ | Auditoría legal UC-F06 |
| `/exploration` | `Exploration` | ✅ | ✅ | Wizard UC-F11 |
| `/certificates` | `Certificates` | ✅ | ✅ | Certificados UC-F10 |
| `/profile` | `Profile` | ✅ | ✅ | Perfil de usuario |
| `/credits` | `Credits` | ✅ | ✅ | Compra de créditos |
| `/payment/return` | `PaymentReturnPage` | ✅ | ✅ | Callback MercadoPago |
| `/citizen-report` | `CitizenReport` | ❌ | ✅ | Reportes ciudadanos UC-09 |
| `/shelters` | `Shelters` | ❌ | ✅ | Refugios UC-04 |
| `/contact` | `Contact` | ❌ | ✅ | Formulario contacto UC-F01 |
| `/faq` | `Faq` | ❌ | ✅ | Preguntas frecuentes |
| `/manual` | `Manual` | ❌ | ✅ | Manual de usuario |
| `/glossary` | `Glossary` | ❌ | ✅ | Glosario |
| `*` | `NotFound` | ❌ | ✅ | 404 page |

### 3.2 Route Configuration (App.tsx)

```tsx
export default function App() {
  return (
    <ThemeProvider>
      <I18nProvider>
        <AuthProvider>
          <BrowserRouter>
            <AppShell>
              <Suspense fallback={<AppLoading />}>
                <Routes>
                  {/* Public routes */}
                  <Route path="/" element={<HomePage />} />
                  <Route path="/login" element={<LoginPage />} />
                  <Route path="/register" element={<RegisterPage />} />
                  <Route path="/map" element={<MapPage />} />
                  <Route path="/contact" element={<ContactPage />} />
                  
                  {/* Protected routes */}
                  <Route
                    path="/fires"
                    element={
                      <ProtectedRoute>
                        <FireHistoryPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/audit"
                    element={
                      <ProtectedRoute>
                        <AuditPage />
                      </ProtectedRoute>
                    }
                  />
                  {/* ... etc */}
                  
                  {/* 404 */}
                  <Route path="*" element={<NotFoundPage />} />
                </Routes>
              </Suspense>
            </AppShell>
          </BrowserRouter>
        </AuthProvider>
      </I18nProvider>
    </ThemeProvider>
  )
}
```

### 3.3 ProtectedRoute Component

```tsx
// components/auth/ProtectedRoute.tsx
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return <AppLoading />
  }

  if (!user) {
    // Redirect to login with return URL
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <>{children}</>
}
```

---

## 4. State Management

### 4.1 AuthContext

**Ubicación**: `src/context/AuthContext.tsx`

**Propósito**: Gestión de autenticación con Supabase Auth

```tsx
interface AuthContextValue {
  user: User | null
  session: Session | null
  isLoading: boolean
  signInWithGoogle: () => Promise<void>
  signUpWithEmail: (payload: SignUpPayload) => Promise<void>
  signInWithEmail: (email: string, password: string) => Promise<void>
  signOut: () => Promise<void>
  credits: number
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [credits, setCredits] = useState(0)

  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
      if (session) {
        fetchUserData(session.user.id)
      }
      setIsLoading(false)
    })

    // Listen to auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        setSession(session)
        if (session) {
          fetchUserData(session.user.id)
        } else {
          setUser(null)
          setCredits(0)
        }
      }
    )

    return () => subscription.unsubscribe()
  }, [])

  const signInWithGoogle = useCallback(async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: window.location.origin },
    })
    if (error) throw error
  }, [])

  const signUpWithEmail = useCallback(async (payload: SignUpPayload) => {
    const { error } = await supabase.auth.signInWithOtp({
      email: payload.email,
      options: {
        data: {
          full_name: `${payload.firstName} ${payload.lastName}`,
          first_name: payload.firstName,
          last_name: payload.lastName,
        },
        emailRedirectTo: window.location.origin,
      },
    })
    if (error) throw error
  }, [])

  const fetchUserData = async (userId: string) => {
    // Call /api/v1/auth/me to sync Supabase user to local DB
    const response = await api.get('/auth/me')
    setUser(response.data)
    setCredits(response.data.credits_balance || 0)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        isLoading,
        signInWithGoogle,
        signUpWithEmail,
        signInWithEmail,
        signOut,
        credits,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}
```

**JWT Injection**:
```tsx
// src/services/api.ts
import axios from 'axios'
import { supabase } from '@/lib/supabase'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
})

// Inject JWT token in all requests
api.interceptors.request.use(async (config) => {
  if (import.meta.env.VITE_USE_SUPABASE_JWT === 'true') {
    const { data: { session } } = await supabase.auth.getSession()
    if (session?.access_token) {
      config.headers.Authorization = `Bearer ${session.access_token}`
    }
  }
  return config
})

export default api
```

---

### 4.2 LanguageContext

**Ubicación**: `src/context/LanguageContext.tsx`

**Propósito**: Internacionalización (i18n) Español/Inglés

```tsx
interface LanguageContextValue {
  language: 'es' | 'en'
  setLanguage: (lang: 'es' | 'en') => void
  t: (key: string) => string
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<'es' | 'en'>('es')

  const t = useCallback(
    (key: string) => {
      return translations[language][key] || key
    },
    [language]
  )

  useEffect(() => {
    // Persist to localStorage
    localStorage.setItem('forestguard_language', language)
  }, [language])

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  )
}
```

**Ejemplo de uso**:
```tsx
import { useLanguage } from '@/hooks/useLanguage'

function MyComponent() {
  const { t, language, setLanguage } = useLanguage()
  
  return (
    <div>
      <h1>{t('welcome_message')}</h1>
      <button onClick={() => setLanguage(language === 'es' ? 'en' : 'es')}>
        {language === 'es' ? 'English' : 'Español'}
      </button>
    </div>
  )
}
```

---

## 5. Pages (20 páginas)

### 5.1 Home (Landing Page)

**Ubicación**: `src/pages/Home.tsx`  
**Auth**: No requerida  
**Componentes clave**:
- `AnimatedGradientText` (H1 con animación)
- `LoginForm` o redirect si autenticado

**Estructura**:
```tsx
export default function Home() {
  const { user } = useAuth()
  
  if (user) {
    return <Navigate to="/fires" />
  }

  return (
    <div className="min-h-screen flex flex-col lg:flex-row">
      {/* Left: Hero + Form */}
      <div className="flex-1 flex flex-col justify-center px-6 py-12">
        <AnimatedGradientText
          as="h1"
          text="La huella del fuego, vista desde el espacio."
          className="text-4xl lg:text-5xl font-bold"
        />
        <h2 className="text-xl text-gray-600 mt-4">
          Genera líneas de tiempo satelitales de incendios en Argentina.
        </h2>
        <p className="text-gray-500 mt-2">
          Compara el antes y el después: detecta revegetación natural o
          construcciones no autorizadas en zonas afectadas.
        </p>
        
        <LoginForm className="mt-8" />
      </div>
      
      {/* Right: Hero Image */}
      <div className="hidden lg:block lg:flex-1 relative">
        <img
          src="/images/forest-hero.webp"
          alt=""
          loading="lazy"
          className="absolute inset-0 w-full h-full object-cover"
        />
      </div>
    </div>
  )
}
```

---

### 5.2 FireHistory (Dashboard UC-F03)

**Ubicación**: `src/pages/FireHistory.tsx` (49KB)  
**Auth**: ✅ Requerida  
**Componentes**:
- `FireFilters` (provincia, fecha, área)
- `FireStatsCards` (total incendios, superficie, etc.)
- `FireTable` con paginación
- `ExportButton` (CSV/JSON)

**Hooks utilizados**:
```tsx
const { data, isLoading, error } = useFires({
  province: selectedProvince,
  startDate,
  endDate,
  minArea,
  page,
  pageSize: 20,
})
```

**Features**:
- Filtrado en tiempo real con debounce (500ms)
- Paginación server-side
- Export a CSV/JSON
- Vista de cards (mobile) / tabla (desktop)
- Guardado de filtros favoritos en `user_saved_filters`

---

### 5.3 Audit (Auditoría Legal UC-F06)

**Ubicación**: `src/pages/Audit.tsx` (24KB)  
**Auth**: ✅ Requerida con API Key

**Flujo**:
1. Usuario ingresa coordenadas o hace click en mapa
2. Selecciona radio de búsqueda (500m - 5000m)
3. Click en "Consultar"
4. POST `/api/v1/audit/land-use`
5. Muestra resultados con evidencia satelital

**Componentes**:
```tsx
function AuditPage() {
  const [location, setLocation] = useState<{ lat: number; lon: number } | null>()
  const [radius, setRadius] = useState(5000)
  const [result, setResult] = useState<AuditResult | null>(null)

  const handleSubmit = async () => {
    const response = await auditService.landUseAudit({
      latitude: location.lat,
      longitude: location.lon,
      search_radius_meters: radius,
    })
    setResult(response.data)
  }

  return (
    <div className="container py-8">
      <h1>Auditoría Legal de Uso del Suelo</h1>
      
      <div className="grid lg:grid-cols-2 gap-8">
        {/* Left: Form + Map */}
        <div>
          <AuditForm
            location={location}
            radius={radius}
            onLocationChange={setLocation}
            onRadiusChange={setRadius}
            onSubmit={handleSubmit}
          />
          <LeafletMap
            center={[-31.4, -64.18]}
            onClick={(latlng) => setLocation(latlng)}
          />
        </div>
        
        {/* Right: Results */}
        <div>
          {result && <AuditResults data={result} />}
        </div>
      </div>
    </div>
  )
}
```

**Resultados mostrados**:
- ¿Viola Ley 26.815? (badge rojo/verde)
- Fecha de prohibición hasta
- Lista de incendios encontrados con:
  - Distancia al punto consultado
  - Thumbnails satelitales
  - Área protegida afectada (si aplica)

---

### 5.4 Exploration (Wizard UC-F11)

**Ubicación**: `src/pages/Exploration.tsx` (51KB)  
**Auth**: ✅ Requerida + Créditos

**Wizard steps**:
1. **Selección de incendio** (autocomplete)
2. **Configuración** (tipo de reporte, rango temporal, visualizaciones)
3. **Preview** (muestra créditos a cobrar)
4. **Confirmación** (procesa pago + dispara Celery worker)
5. **Polling** (muestra progreso hasta completion)
6. **Download** (PDF con hash SHA-256)

**Hooks**:
```tsx
const { createInvestigation, getInvestigation } = useExploration()

const handleSubmit = async (config: ExplorationConfig) => {
  // Create investigation
  const investigation = await createInvestigation({
    fire_event_id: selectedFire.id,
    investigation_type: 'historical',
    config,
  })
  
  // Poll for completion
  const interval = setInterval(async () => {
    const updated = await getInvestigation(investigation.id)
    if (updated.status === 'completed') {
      clearInterval(interval)
      // Show download button
    }
  }, 5000)
}
```

**UI Estados**:
- `draft`: Wizard activo
- `processing`: Loading spinner + "Generando reporte..." (30-120s)
- `completed`: Botón "Descargar PDF" + hash verificable
- `failed`: Error message + retry button

---

### 5.5 MapPage (Mapa Interactivo M1/V1)

**Ubicación**: `src/pages/MapPage.tsx`  
**Auth**: ❌ Pública

**Features**:
- Mapa base Leaflet (OpenStreetMap)
- Marcadores de incendios activos
- Heatmap H3 de recurrencia
- Capas de áreas protegidas
- Panel lateral con filtros
- Popup con info al hacer click

**Componentes**:
```tsx
function MapPage() {
  const { data: fires } = useFires({ status: 'active' })
  const { data: h3Cells } = useRecurrenceHeatmap()

  return (
    <div className="h-full flex">
      {/* Sidebar */}
      <MapSidebar filters={filters} onFilterChange={setFilters} />
      
      {/* Map */}
      <LeafletMap center={[-34.6, -58.4]} zoom={6}>
        {/* Fire markers */}
        {fires?.items.map((fire) => (
          <FireMarker key={fire.id} fire={fire} />
        ))}
        
        {/* H3 Heatmap */}
        <H3HeatmapLayer cells={h3Cells} />
        
        {/* Protected areas */}
        <ProtectedAreaLayer />
      </LeafletMap>
    </div>
  )
}
```

**H3 Heatmap**:
```tsx
// components/map/H3HeatmapLayer.tsx
import { Polygon } from 'react-leaflet'
import { h3ToGeoBoundary } from 'h3-js'

export function H3HeatmapLayer({ cells }: { cells: H3Cell[] }) {
  return (
    <>
      {cells.map((cell) => {
        const boundary = h3ToGeoBoundary(cell.h3_index)
        const color = getColorByRecurrence(cell.recurrence_class)
        
        return (
          <Polygon
            key={cell.h3_index}
            positions={boundary}
            pathOptions={{ fillColor: color, fillOpacity: 0.6 }}
          />
        )
      })}
    </>
  )
}
```

---

## 6. Components (93 componentes)

### 6.1 shadcn/ui Components (43)

**Ubicación**: `src/components/ui/`

Biblioteca de componentes accesibles basada en Radix UI + TailwindCSS.

| Componente | Propósito | Radix Base |
|-----------|-----------|------------|
| `Button` | Botones con variantes | - |
| `Input` | Text inputs | - |
| `Card` | Contenedores con sombra | - |
| `Dialog` | Modales | `Dialog` |
| `Select` | Dropdowns | `Select` |
| `Checkbox` | Checkboxes | `Checkbox` |
| `RadioGroup` | Radio buttons | `RadioGroup` |
| `Tabs` | Pestañas | `Tabs` |
| `Accordion` | Acordeones | `Accordion` |
| `Alert` | Alertas/notificaciones | - |
| `Badge` | Badges para estados | - |
| `Table` | Tablas responsivas | - |
| `Skeleton` | Loading placeholders | - |
| `Tooltip` | Tooltips accesibles | `Tooltip` |
| `Popover` | Popovers | `Popover` |
| ... | ... | ... |

**Ejemplo Button**:
```tsx
// components/ui/button.tsx
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'

const buttonVariants = cva(
  'inline-flex items-center justify-center rounded-lg font-medium transition-colors',
  {
    variants: {
      variant: {
        default: 'bg-emerald-600 text-white hover:bg-emerald-700',
        outline: 'border border-gray-200 bg-white hover:bg-gray-50',
        ghost: 'hover:bg-gray-100',
        destructive: 'bg-red-600 text-white hover:bg-red-700',
      },
      size: {
        sm: 'h-9 px-3 text-sm',
        md: 'h-10 px-4',
        lg: 'h-11 px-6 text-lg',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'md',
    },
  }
)

export function Button({ variant, size, className, ...props }: ButtonProps) {
  return (
    <button
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  )
}
```

---

### 6.2 Map Components (12)

#### LeafletMap

```tsx
// components/map/LeafletMap.tsx
import { MapContainer, TileLayer } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

export function LeafletMap({ center, zoom, children, onClick }: MapProps) {
  return (
    <MapContainer
      center={center}
      zoom={zoom}
      className="h-full w-full"
      onClick={(e) => onClick?.(e.latlng)}
    >
      <TileLayer
        attribution='&copy; OpenStreetMap'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {children}
    </MapContainer>
  )
}
```

#### FireMarker

```tsx
// components/map/FireMarker.tsx
import { Marker, Popup } from 'react-leaflet'
import { Icon } from 'leaflet'

const fireIcon = new Icon({
  iconUrl: '/icons/fire-marker.png',
  iconSize: [32, 32],
})

export function FireMarker({ fire }: { fire: FireEvent }) {
  return (
    <Marker position={[fire.centroid.lat, fire.centroid.lon]} icon={fireIcon}>
      <Popup>
        <div className="min-w-[200px]">
          <h3 className="font-bold">{fire.province}</h3>
          <p className="text-sm text-gray-600">
            Inicio: {formatDate(fire.start_date)}
          </p>
          <p className="text-sm">
            Área: {fire.estimated_area_hectares.toFixed(1)} ha
          </p>
          <Button size="sm" className="mt-2" asChild>
            <Link to={`/fires/${fire.id}`}>Ver detalle</Link>
          </Button>
        </div>
      </Popup>
    </Marker>
  )
}
```

---

### 6.3 Dashboard Components (15)

#### FireStatsCard

```tsx
// components/dashboard/FireStatsCard.tsx
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { TrendingUp, TrendingDown } from 'lucide-react'

export function FireStatsCard({ title, value, trend, icon: Icon }: StatsCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {trend && (
          <p className="text-xs text-muted-foreground flex items-center gap-1">
            {trend > 0 ? (
              <TrendingUp className="h-3 w-3 text-red-500" />
            ) : (
              <TrendingDown className="h-3 w-3 text-green-500" />
            )}
            {Math.abs(trend)}% vs. mes anterior
          </p>
        )}
      </CardContent>
    </Card>
  )
}
```

---

## 7. Services (API Clients)

### 7.1 Base API Setup

```tsx
// services/api.ts
import axios from 'axios'
import { supabase } from '@/lib/supabase'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 30000,
})

// Request interceptor: inject JWT
api.interceptors.request.use(async (config) => {
  if (import.meta.env.VITE_USE_SUPABASE_JWT === 'true') {
    const { data: { session } } = await supabase.auth.getSession()
    if (session?.access_token) {
      config.headers.Authorization = `Bearer ${session.access_token}`
    }
  }
  
  // Inject X-Request-ID for tracing
  config.headers['X-Request-ID'] = crypto.randomUUID()
  
  return config
})

// Response interceptor: handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to login
      window.location.href = '/login'
    }
    throw error
  }
)

export default api
```

---

### 7.2 Service Modules

#### fireService.ts

```tsx
// services/fireService.ts
import api from './api'
import type { FireEvent, FireFilters, PaginatedResponse } from '@/types'

export const fireService = {
  async getFires(filters: FireFilters): Promise<PaginatedResponse<FireEvent>> {
    const { data } = await api.get('/api/v1/fires', { params: filters })
    return data
  },

  async getFireById(id: string): Promise<FireEvent> {
    const { data } = await api.get(`/api/v1/fires/${id}`)
    return data
  },

  async getStats(province?: string): Promise<FireStats> {
    const { data } = await api.get('/api/v1/fires/stats', {
      params: { province },
    })
    return data
  },

  async exportFires(filters: FireFilters, format: 'csv' | 'json'): Promise<Blob> {
    const { data } = await api.get('/api/v1/fires/export', {
      params: { ...filters, format },
      responseType: 'blob',
    })
    return data
  },
}
```

#### auditService.ts

```tsx
// services/auditService.ts
export const auditService = {
  async landUseAudit(payload: AuditRequest): Promise<AuditResult> {
    const { data } = await api.post('/api/v1/audit/land-use', payload, {
      headers: { 'X-API-Key': import.meta.env.VITE_API_KEY },
    })
    return data
  },
}
```

#### explorationService.ts

```tsx
// services/explorationService.ts
export const explorationService = {
  async createInvestigation(
    payload: CreateInvestigationPayload
  ): Promise<Investigation> {
    const { data } = await api.post('/api/v1/explorations', payload)
    return data
  },

  async getInvestigation(id: string): Promise<Investigation> {
    const { data } = await api.get(`/api/v1/explorations/${id}`)
    return data
  },

  async listInvestigations(): Promise<Investigation[]> {
    const { data } = await api.get('/api/v1/explorations')
    return data
  },
}
```

---

## 8. Custom Hooks (17 hooks)

### 8.1 Data Fetching Hooks

#### useFires

```tsx
// hooks/useFires.ts
import { useQuery } from '@tanstack/react-query'
import { fireService } from '@/services/fireService'

export function useFires(filters: FireFilters) {
  return useQuery({
    queryKey: ['fires', filters],
    queryFn: () => fireService.getFires(filters),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}
```

#### useFireDetail

```tsx
// hooks/useFireDetail.ts
export function useFireDetail(id: string) {
  return useQuery({
    queryKey: ['fire', id],
    queryFn: () => fireService.getFireById(id),
    enabled: !!id,
  })
}
```

---

### 8.2 Utility Hooks

#### useDebounce

```tsx
// hooks/useDebounce.ts
import { useState, useEffect } from 'react'

export function useDebounce<T>(value: T, delay: number = 500): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => clearTimeout(handler)
  }, [value, delay])

  return debouncedValue
}
```

**Uso**:
```tsx
function SearchComponent() {
  const [searchTerm, setSearchTerm] = useState('')
  const debouncedSearch = useDebounce(searchTerm, 500)

  const { data } = useFires({ search: debouncedSearch })
}
```

#### useIntersectionObserver

```tsx
// hooks/useIntersectionObserver.ts
export function useIntersectionObserver(
  ref: RefObject<Element>,
  options: IntersectionObserverInit = {}
) {
  const [isIntersecting, setIsIntersecting] = useState(false)

  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => {
      setIsIntersecting(entry.isIntersecting)
    }, options)

    if (ref.current) {
      observer.observe(ref.current)
    }

    return () => observer.disconnect()
  }, [ref, options])

  return isIntersecting
}
```

**Uso (lazy loading de imágenes)**:
```tsx
function LazyImage({ src }: { src: string }) {
  const ref = useRef<HTMLImageElement>(null)
  const isVisible = useIntersectionObserver(ref)

  return (
    <img
      ref={ref}
      src={isVisible ? src : '/placeholder.png'}
      loading="lazy"
    />
  )
}
```

---

## 9. Styling System

### 9.1 TailwindCSS Configuration

```js
// tailwind.config.js
export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        // ... etc
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
}
```

### 9.2 CSS Variables (globals.css)

```css
/* src/index.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --primary: 142 76% 36%;  /* emerald-600 */
    --primary-foreground: 0 0% 100%;
    /* ... */
  }

  .dark {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;
    /* ... */
  }
}

@layer components {
  .container {
    @apply mx-auto max-w-7xl px-4 sm:px-6 lg:px-8;
  }
}
```

---

## 10. Performance Optimizations

### 10.1 Code Splitting

**Lazy Loading de páginas**:
```tsx
const HomePage = lazy(() => import('@/pages/Home'))
const FireHistoryPage = lazy(() => import('@/pages/FireHistory'))
// etc...
```

**Suspense Boundary**:
```tsx
<Suspense fallback={<AppLoading />}>
  <Routes>...</Routes>
</Suspense>
```

### 10.2 Image Optimization

**Lazy Loading con Intersection Observer**:
```tsx
<img src={url} loading="lazy" decoding="async" />
```

**Responsive Images**:
```tsx
<picture>
  <source srcSet="/hero.avif" type="image/avif" />
  <source srcSet="/hero.webp" type="image/webp" />
  <img src="/hero.jpg" alt="" />
</picture>
```

### 10.3 React Query Cache

```tsx
// main.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 min
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

<QueryClientProvider client={queryClient}>
  <App />
</QueryClientProvider>
```

---

## 11. Testing

### 11.1 Unit Tests (Vitest)

```tsx
// __tests__/components/Button.test.tsx
import { render, screen } from '@testing-library/react'
import { Button } from '@/components/ui/button'

describe('Button', () => {
  it('renders with correct text', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByText('Click me')).toBeInTheDocument()
  })

  it('handles click events', async () => {
    const handleClick = vi.fn()
    render(<Button onClick={handleClick}>Click</Button>)
    
    await userEvent.click(screen.getByText('Click'))
    expect(handleClick).toHaveBeenCalledOnce()
  })
})
```

### 11.2 E2E Tests (Cypress)

```tsx
// cypress/e2e/login.cy.ts
describe('Login Flow', () => {
  beforeEach(() => {
    cy.visit('/login')
  })

  it('should login with Google OAuth', () => {
    cy.get('[data-testid="login-google"]').click()
    // Mock OAuth flow
    cy.url().should('include', '/fires')
  })

  it('should show validation errors', () => {
    cy.get('[data-testid="login-email"]').type('invalid')
    cy.get('[data-testid="login-submit"]').click()
    cy.get('[data-testid="login-error"]').should('be.visible')
  })
})
```

---

## 12. Build & Deployment

### 12.1 Vite Configuration

```ts
// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          leaflet: ['leaflet', 'react-leaflet'],
        },
      },
    },
  },
})
```

### 12.2 Environment Variables

```bash
# .env
VITE_API_BASE_URL=https://api.forestguard.ar
VITE_SUPABASE_URL=https://<project>.supabase.co
VITE_SUPABASE_ANON_KEY=<anon-key>
VITE_USE_SUPABASE_JWT=true
VITE_API_KEY=<api-key-for-public-endpoints>
```

### 12.3 Production Build

```bash
# Build
npm run build

# Preview
npm run preview

# Deploy (via Nginx)
cp -r dist/* /var/www/forestguard/
```

---

**Documento generado**: Febrero 2026  
**Próxima actualización**: Post-refactor de componentes UI
