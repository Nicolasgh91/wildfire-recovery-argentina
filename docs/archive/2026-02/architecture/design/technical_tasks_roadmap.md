# ForestGuard - Plan de tareas técnicas actualizado

**Fecha:** 2026-02-10  
**Versión:** 6.0  
**Objetivo:** Consolidar cambios de UI/UX, optimizar clustering GEE y completar wizard de exploración satelital

---

## Resumen de cambios respecto a versión anterior

| Área | Cambios |
|------|---------|
| Nomenclatura | `Audit` → **Verificar terreno**, `Certificates` → **Exploración satelital** |
| Moneda | USD → **ARS** para costos de imágenes HD |
| Clustering | Optimización de parámetros para reducir candidatos GEE |
| UI/UX | Correcciones críticas en mapa, histórico y wizard |

---

## 1. Estado actual del proyecto

```
PROGRESO GENERAL
════════════════
Tareas completadas:     26/32 (81%)
Casos de uso MVP:       9/10  (solo falta UC-F11)
Tareas nuevas (ajustes): 18
Total pendiente:        6 tareas
Días estimados:         ~30 días
```

### 1.1 Validación técnica de ajustes propuestos

| Sección | Viabilidad | Observaciones |
|---------|------------|---------------|
| 1. Actualización de documentación | ✅ Viable | Refactor de nombres sin impacto en código |
| 2. Optimización clustering GEE | ✅ Viable | Parámetros en `system_parameters`, versionado existente |
| 3.A Performance histórico | ✅ Viable | Requiere análisis de queries + índices |
| 3.A.2 Error botón "Ver detalle" | ✅ Viable | Bug de navegación reproducible |
| 3.B Verificar terreno | ✅ Viable | Endpoint `/api/v1/audit/land-use` operativo |
| 3.C Exploración satelital | ✅ Viable | Celery disponible en cola `analysis` |
| 5. Wizard exploración ARS | ✅ Viable | Backend soporta ARS, requiere task Celery |

---

## 2. Estructura de fases actualizada

```
FASE 4: Hardening y seguridad (~7 días)
├── T4.1 Security & Hard Caps [REALIZADO]
├── T4.2 Performance & Documentación [REALIZADO]
└── T4.3 Resilience & Cleanup [REALIZADO]

FASE 5: Exploración satelital (~10 días)
├── T5.1 Wizard exploración (3 pasos) [REALIZADO]
├── T5.2 Series históricas [REALIZADO]
└── T5.3 PDF con hash y QR [REALIZADO]

FASE 6: Testing y observabilidad (~7 días)
├── T6.1 Tests unitarios [COMPLETADO]
├── T6.2 Tests integración [COMPLETADO]
├── T6.3 Tests E2E [COMPLETADO]
└── T6.4 Monitoreo y alertas [COMPLETADO]

FASE 7: Ajustes UI/UX (NUEVA) (~6 días)
├── T7.1 Actualización documentación [REALIZADO]
├── T7.2 Optimización clustering GEE [REALIZADO]
├── T7.3 Performance histórico [REALIZADO]
├── T7.4 Corrección navegación mapa [REALIZADO]
├── T7.5 Página verificar terreno [NUEVO]
├── T7.6 Ajustes exploración satelital [NUEVO]
└── T7.7 Activos + Recientes + Home/Mapa/Audit [REALIZADO]
```

---

## 3. Tareas técnicas detalladas

> **INSTRUCCIONES PARA EL AGENTE DE CÓDIGO:**
> 1. Ejecutar tareas en orden de prioridad
> 2. Verificar criterios de aceptación después de cada cambio
> 3. Crear commits atómicos con mensajes descriptivos
> 4. NO inventar funcionalidades no especificadas

---

### FASE 7: Ajustes UI/UX

#### T7.1 Actualización de documentación y nomenclatura

**Prioridad:** P1  
**Esfuerzo:** 2 horas  
**Dependencias:** Ninguna

##### T7.1.1 Refactor de nombres en documentación

**Archivos a modificar:**
- `/mnt/project/2_casos_de_uso_final.md`
- `/mnt/project/3_technical_roadmap.md`
- `/mnt/project/0_master_plan.md`

**Cambios requeridos:**

| Término anterior | Término nuevo |
|------------------|---------------|
| Audit | Verificar terreno |
| Auditoría legal | Verificación de terreno |
| Certificates | Exploración satelital |
| Certificación legal | Exploración satelital |
| USD 0.50 por imagen | ARS por imagen (según pricing backend) |

**Verificación:**
```bash
grep -rn "Audit\|Certificate\|USD 0.50" /mnt/project/*.md
# Debe retornar vacío tras los cambios
```

##### T7.1.2 Crear caso de uso para landing page

**Archivo:** `/mnt/project/2_casos_de_uso_final.md`

**Contenido a agregar:**

```markdown
### UC-F14: Landing page pública

ID y nombre (final): UC-F14 - Landing page pública
Complejidad: baja
Objetivo: presentar la plataforma y guiar hacia registro/login.
Actores: usuario no autenticado.
Precondiciones: ninguna.
Disparador: acceso a URL raíz (/).

Flujo principal:
1. Usuario accede a la landing page.
2. Sistema muestra hero, beneficios y CTA.
3. Usuario puede navegar a /login o /register.

Reglas de negocio:
- No requiere autenticación.
- Estadísticas públicas vía UC-F02.
- Sin acceso a funcionalidades autenticadas.

Estado actual: implementado
```

##### T7.1.3 Documentar regla de deslogueo

**Archivo:** `/mnt/project/2_casos_de_uso_final.md`

**Contenido a agregar:**

```markdown
### Regla transversal: cierre de sesión

Disparador: click en "Salir" desde navbar.
Resultado:
1. Invalidar sesión en AuthContext.
2. Limpiar tokens de localStorage/sessionStorage.
3. Redirect automático a /login.

Implementación:
- Frontend: AuthContext.logout() + useNavigate('/login')
- Backend: invalidar refresh token si aplica.
```

---

#### T7.2 Optimización del clustering de eventos GEE

**Prioridad:** P0 (crítico para reducir costos GEE)  
**Esfuerzo:** 4 horas  
**Dependencias:** Ninguna

##### T7.2.1 Análisis del algoritmo actual

**Archivo a revisar:** `workers/tasks/clustering_task.py`

**Checklist de análisis:**
- [ ] Identificar umbral espacial actual (eps en DBSCAN)
- [ ] Identificar ventana temporal actual
- [ ] Documentar condiciones de corte de episodios
- [ ] Contar candidatos GEE actuales (objetivo: reducir de 8 a ≤3)

**Entregable:** `docs/tech/clustering_analysis.md`

##### T7.2.2 Ajuste de parámetros de clustering

**Fuente:** tabla `clustering_versions` (versión activa)

**Parámetros a revisar en `clustering_versions`:**

| Parámetro | Valor actual (est.) | Valor propuesto | Justificación |
|-----------|---------------------|-----------------|---------------|
| `epsilon_km` | 1.0 | 2.5 | Aumentar tolerancia espacial |
| `temporal_window_hours` | 24 | 48 | Agregar eventos cercanos en tiempo |
| `min_points` | 3 | 2 | Permitir episodios más pequeños |

**Cambio requerido:**

```sql
-- Actualizar parámetros via versionado (migración Alembic)
UPDATE clustering_versions
SET is_active = false
WHERE is_active = true;

INSERT INTO clustering_versions (
  version_name,
  epsilon_km,
  min_points,
  temporal_window_hours,
  algorithm,
  change_reason,
  is_active
) VALUES (
  'v2.0-optimized',
  2.5,
  2,
  48,
  'ST-DBSCAN',
  'T7.2 optimization',
  true
);
```

##### T7.2.3 Ejecución en modo dry-run

**Comando:**
```bash
python -m workers.tasks.clustering_task --dry-run --verbose
```

**Notas:**
- Soporta `--days-back` y `--max-events`
- `--dry-run` hace rollback y no persiste cambios

**Criterios de aceptación:**
- [ ] Cantidad de `fire_episodes` < cantidad actual
- [ ] Candidatos GEE ≤ 3 por episodio
- [ ] No hay pérdida de eventos (todos asignados)

##### T7.2.4 Versionado de parámetros

**Archivo:** Migración SQL

```sql
-- Crear nueva versión de clustering
INSERT INTO clustering_versions (
  version_name,
  epsilon_km,
  min_points,
  temporal_window_hours,
  algorithm,
  change_reason,
  is_active
) VALUES (
  'v2.0-optimized',
  2.5,
  2,
  48,
  'ST-DBSCAN',
  'T7.2 optimization',
  true
);

-- Desactivar versión anterior
UPDATE clustering_versions 
SET is_active = false
WHERE version_name != 'v2.0-optimized';
```

---

#### T7.3 Performance en histórico de incendios

**Prioridad:** P1  
**Esfuerzo:** 3 horas  
**Dependencias:** Ninguna

##### T7.3.1 Análisis de cuellos de botella

**Herramientas:**
- PostgreSQL: `EXPLAIN ANALYZE` en queries principales
- Frontend: Chrome DevTools Performance tab

**Queries a analizar:**
```sql
-- Query principal de /api/v1/fires
EXPLAIN ANALYZE
SELECT * FROM fire_events 
WHERE start_date >= '2025-01-01' 
ORDER BY start_date DESC 
LIMIT 50;

-- Query de stats
EXPLAIN ANALYZE
SELECT COUNT(*), SUM(area_hectares), AVG(frp_max)
FROM fire_events
WHERE start_date >= '2025-01-01';
```

##### T7.3.2 Optimizaciones de backend

**Archivo:** `app/api/v1/fires.py`

**Cambios requeridos:**

1. **Paginación con cursor** (en lugar de offset):
```python
# ANTES
.offset((page - 1) * page_size)

# DESPUÉS
.filter(fire_events.id < cursor_id) if cursor_id else True
```

2. **Índice compuesto para ordenamiento:**
```sql
CREATE INDEX CONCURRENTLY idx_fire_events_start_date_id 
ON fire_events (start_date DESC, id DESC);
```

##### T7.3.3 Optimizaciones de frontend

**Archivo:** `src/pages/FireHistory.tsx`

**Cambios requeridos:**

1. **Memoización de componentes:**
```tsx
const FireRow = React.memo(({ fire }: { fire: FireEvent }) => {
  // ...
});
```

2. **Virtualización de lista:**
```tsx
import { useVirtualizer } from '@tanstack/react-virtual';

// Implementar lista virtualizada para >100 items
```

3. **Skeleton loader:**
```tsx
{isLoading && <FireHistorySkeleton count={10} />}
```

---

#### T7.4 Corrección de navegación desde mapa

**Prioridad:** P0 (bug crítico)  
**Esfuerzo:** 2 horas  
**Dependencias:** Ninguna

##### T7.4.1 Reproducir y diagnosticar error

**Pasos de reproducción:**
1. Ir a `/map`
2. Click en un incendio del mapa
3. Click en "Ver detalle"
4. Observar error o comportamiento incorrecto

**Diagnóstico esperado:**
- Comparar `fire_id` del popup vs carrusel
- Verificar consistencia de payload

##### T7.4.2 Corrección del bug

**Archivo:** `src/components/Map/FirePopup.tsx`

**Cambio probable:**
```tsx
// ANTES (hipótesis)
const handleViewDetail = () => {
  navigate(`/fires/${fire.event_id}`);  // ID incorrecto
};

// DESPUÉS
const handleViewDetail = () => {
  navigate(`/fires/${fire.id}`);  // ID correcto
};
```

**Verificación:**
```typescript
// Test E2E
test('navigate to fire detail from map', async ({ page }) => {
  await page.goto('/map');
  await page.click('[data-testid="fire-marker"]');
  await page.click('[data-testid="view-detail-btn"]');
  await expect(page).toHaveURL(/\/fires\/[a-f0-9-]+/);
});
```

---

#### T7.5 Página "Verificar terreno"

**Prioridad:** P1  
**Esfuerzo:** 4 horas  
**Dependencias:** T7.4

##### T7.5.1 Ajustes de layout

**Archivo:** `src/pages/VerifyLand.tsx`

**Cambios requeridos:**

1. **Eliminar ícono del título:**
```tsx
// ANTES
<h1><IconMap /> Verificar terreno</h1>

// DESPUÉS
<h1>Verificar terreno</h1>
```

2. **Ajustar subtítulos:**
```tsx
<h2 className="w-full text-left">Buscar ubicación</h2>
```

##### T7.5.2 Validaciones de input

**Archivo:** `src/components/VerifyLand/SearchInput.tsx`

**Implementar validaciones:**

```tsx
const validateInput = (value: string, type: 'address' | 'locality' | 'park' | 'province') => {
  const rules = {
    address: { minLength: 5, pattern: /^[a-zA-Z0-9\s,.-]+$/ },
    locality: { minLength: 3, pattern: /^[a-zA-Z\s]+$/ },
    park: { minLength: 3, pattern: /^[a-zA-Z\s]+$/ },
    province: { minLength: 2, pattern: /^[a-zA-Z\s]+$/ },
  };
  
  const rule = rules[type];
  if (value.length < rule.minLength) return `Mínimo ${rule.minLength} caracteres`;
  if (!rule.pattern.test(value)) return 'Formato inválido';
  return null;
};
```

##### T7.5.3 Acción del CTA "Verificá"

**Archivo:** `src/pages/VerifyLand.tsx`

**Request al backend:**
```typescript
const handleVerify = async () => {
  const response = await api.post('/api/v1/audit/land-use', {
    latitude: selectedPoint.lat,
    longitude: selectedPoint.lng,
    radius_meters: 5000,  // 5km default
  });
  
  setResults(response.data);
};
```

##### T7.5.4 Contenido de resultados

**Componentes a implementar:**

1. **Checklist de verificación:**
```tsx
<VerificationChecklist>
  <ChecklistItem status={hasRecentFires ? 'warning' : 'ok'}>
    Incendios recientes (últimos 5 años)
  </ChecklistItem>
  <ChecklistItem status={vegetationRecovery}>
    Recuperación de vegetación
  </ChecklistItem>
  <ChecklistItem status={signalPersistence}>
    Persistencia de señales térmicas
  </ChecklistItem>
  <ChecklistItem status="info">
    Fuentes públicas consultadas
  </ChecklistItem>
</VerificationChecklist>
```

2. **Línea de tiempo:**
```tsx
<Timeline events={fireEvents} />
```

3. **Galería de thumbnails:**
```tsx
<ThumbnailGallery images={satelliteImages} />
```

4. **Instrucción final:**
```tsx
<Alert variant="info">
  Marcá un punto en el mapa y presioná "Verificá" para obtener el informe.
</Alert>
```

---

#### T7.6 Ajustes en exploración satelital

**Prioridad:** P1  
**Esfuerzo:** 4 horas  
**Dependencias:** T7.2

##### T7.6.1 Reutilizar algoritmo de clustering unificado

**Archivo:** `src/pages/Exploration.tsx`

**Cambio requerido:**
```typescript
// ANTES (si existe lógica duplicada)
const groupEvents = (events) => { /* lógica local */ };

// DESPUÉS
import { groupEventsByEpisode } from '@/services/clustering';
const episodes = groupEventsByEpisode(events);
```

##### T7.6.2 Correccion de acceso al paso 3 (auth flow)

**Archivos:**
- `frontend/src/services/endpoints/explorations.ts`
- `frontend/src/services/api.ts`
- `frontend/src/pages/Exploration.tsx`

**Problemas detectados y correcciones (Issue 1-3):**

**Issue 1 - Redireccion global de auth en Step 3:**
- Problema: los 401 en endpoints del paso 3 disparaban la redireccion global a `/login`, perdiendo el estado del wizard.
- Fix: se agrega `X-Skip-Auth-Redirect: true` en endpoints del step 3 (create/update/add/delete/quote/generate) para manejar el 401 localmente en `Exploration.tsx` y mostrar el modal de login sin perder estado.

**Issue 2 - Modal de login en Step 2:**
- Problema: el modal de login aparecia en Step 2 ante errores de preview/seleccion.
- Fix: `handleSelectFire` no muestra modal de login; el auth gate se concentra solo en el avance a Step 3 via `handleContinueToStep3`.

**Issue 3 - Loop recursivo de 401 en Step 3:**
- Problema: loop infinito de POST `/explorations/` con 401 por auto-sync continuo.
- Fix: se implementa `pauseAutoSync` para detener `syncDraftAndQuote` cuando aparece el modal de auth o ante un 401. El boton "Volver atras" del modal ahora vuelve a Step 2 (`setStep(2)`).

##### T7.6.3 Eliminar ícono en título

**Archivo:** `src/pages/Exploration.tsx`

```tsx
// ANTES
<h1><IconSatellite /> Explorá la evolución del terreno</h1>

// DESPUÉS
<h1>Explorá la evolución del terreno</h1>
```

---

#### T7.7 Activos + Recientes + Home/Mapa/Audit (COMPLETADO)

**Prioridad:** P1  
**Esfuerzo:** 6 horas  
**Dependencias:** Ninguna

**Descripción breve:** Ajustes UI/UX para mostrar episodios activos y recientes en Home/Mapa, y habilitar búsqueda histórica en Audit.

**Checklist de entrega:**
- [x] Backend: `GET /api/v1/fire-episodes` con `mode=active|recent` y orden por `end_date` en recent.
- [x] Backend: `representative_event_id` + `centroid_lat/lon` en listados.
- [x] Frontend Home: toggle “Ver recientes”, fallback automático si no hay activos, dedupe.
- [x] Frontend Mapa: episodios reales (activos+recientes) con marcadores por centroide.
- [x] Backend Audit: `GET /api/v1/audit/search` con resolución de lugar.
- [x] Frontend Audit: búsqueda y tarjeta de “Lugar resuelto” + listado histórico.

---

### FASE 5 (actualizada): Wizard de exploración satelital

#### T5.1 Wizard exploración satelital (3 pasos) - COMPLETADO

**Prioridad:** P0  
**Esfuerzo:** 4 días  
**Dependencias:** T7.2, T7.6

##### T5.1.1 Actualizar documentación de pricing

**Archivo:** Roadmap y documentación

**Cambio:**
- Reemplazar "USD 0.50 por imagen HD" → "ARS por imagen (según pricing backend)"
- Mantener límite de 12 imágenes

##### T5.1.2 Backend: tarea Celery para generación HD

**Archivo nuevo:** `workers/tasks/exploration_hd_task.py`

```python
from celery import shared_task
from app.services.exploration_service import run_generation_job

@shared_task(
    name='workers.tasks.exploration_hd_task.generate_exploration_hd',
    queue='analysis',
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
def generate_exploration_hd(self, job_id: str):
    """
    Genera imágenes HD para una exploración.
    
    Args:
        job_id: UUID del HdGenerationJob
    
    Returns:
        dict con status y URLs de imágenes generadas
    """
    try:
        result = run_generation_job(job_id)
        return {
            'status': 'completed',
            'job_id': job_id,
            'images': result.image_urls
        }
    except Exception as e:
        self.retry(exc=e)
```

##### T5.1.3 Registrar tarea en celery_app.py

**Archivo:** `celery_app.py`

```python
celery_app = Celery(
    'forestguard',
    broker='redis://redis:6379/0',
    backend='redis://redis:6379/1',
    include=[
        'workers.tasks.ingestion',
        'workers.tasks.clustering',
        'workers.tasks.recovery',
        'workers.tasks.destruction',
        'workers.tasks.exploration_hd_task',  # NUEVO
    ]
)

# Agregar ruta de cola
task_routes = {
    'workers.tasks.exploration_hd_task.*': {'queue': 'analysis'},
}
```

##### T5.1.4 Modificar endpoint de generación

**Archivo:** `app/api/v1/explorations.py`

```python
from workers.tasks.exploration_hd_task import generate_exploration_hd

@router.post("/{exploration_id}/generate")
async def generate_exploration(
    exploration_id: UUID,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verificar idempotencia
    existing = await check_idempotency(idempotency_key, db)
    if existing:
        return existing
    
    # Verificar créditos
    if not has_sufficient_credits(current_user, exploration_id):
        raise HTTPException(status_code=402, detail="Créditos insuficientes")
    
    # Crear job
    job = await create_hd_generation_job(exploration_id, current_user.id, db)
    
    # Encolar tarea Celery
    generate_exploration_hd.delay(str(job.id))
    
    return ExplorationGenerateResponse(
        job_id=job.id,
        status="queued",
        message="Generación iniciada. Use el job_id para consultar estado."
    )
```

##### T5.1.5 Frontend: inputs de coordenadas

**Archivo:** `src/pages/Exploration.tsx`

```tsx
// Paso 1: Agregar inputs
<div className="grid grid-cols-3 gap-4">
  <Input
    label="Latitud"
    type="number"
    step="0.0001"
    value={latitude}
    onChange={(e) => setLatitude(parseFloat(e.target.value))}
    placeholder="-34.6037"
  />
  <Input
    label="Longitud"
    type="number"
    step="0.0001"
    value={longitude}
    onChange={(e) => setLongitude(parseFloat(e.target.value))}
    placeholder="-58.3816"
  />
  <Input
    label="Radio (metros)"
    type="number"
    min={100}
    max={10000}
    value={radiusMeters}
    onChange={(e) => setRadiusMeters(parseInt(e.target.value))}
    placeholder="5000"
  />
</div>
```

##### T5.1.6 Frontend: conversión de radio a bbox

**Archivo:** `src/services/explorations.ts`

```typescript
export function radiusToBbox(
  lat: number, 
  lng: number, 
  radiusMeters: number
): [number, number, number, number] {
  // Aproximación: 1 grado ≈ 111km
  const latDelta = radiusMeters / 111000;
  const lngDelta = radiusMeters / (111000 * Math.cos(lat * Math.PI / 180));
  
  return [
    lng - lngDelta,  // min_lng
    lat - latDelta,  // min_lat
    lng + lngDelta,  // max_lng
    lat + latDelta,  // max_lat
  ];
}

export async function searchFireEvents(
  latitude: number,
  longitude: number,
  radiusMeters: number
): Promise<FireEvent[]> {
  const bbox = radiusToBbox(latitude, longitude, radiusMeters);
  
  const response = await api.get('/api/v1/fire-events/search', {
    params: { bbox: bbox.join(',') }
  });
  
  return response.data;
}
```

##### T5.1.7 Frontend: confirmación de pago

**Archivo:** `src/pages/Exploration.tsx`

```tsx
import { AlertDialog } from '@/components/ui/AlertDialog';

const [showConfirmDialog, setShowConfirmDialog] = useState(false);

const handleGenerate = () => {
  setShowConfirmDialog(true);
};

const confirmGenerate = async () => {
  try {
    const response = await generateExploration(explorationId, {
      headers: { 'Idempotency-Key': crypto.randomUUID() }
    });
    
    setTrackingId(response.job_id);
    toast.success(`Generación iniciada. ID: ${response.job_id}`);
  } catch (error) {
    if (error.response?.status === 402) {
      toast.error('Créditos insuficientes');
      navigate('/credits');
    }
  } finally {
    setShowConfirmDialog(false);
  }
};

// En el render:
<AlertDialog
  open={showConfirmDialog}
  onOpenChange={setShowConfirmDialog}
  title="Confirmar generación"
  description={`Se descontarán ${totalCost} ARS de tu cuenta. ¿Continuar?`}
  confirmText="Confirmar y generar"
  onConfirm={confirmGenerate}
/>
```

##### T5.1.8 Frontend: mostrar tracking ID

**Archivo:** `src/pages/Exploration.tsx`

```tsx
{trackingId && (
  <Card className="bg-green-50 border-green-200">
    <CardContent className="flex items-center gap-4">
      <IconCheck className="text-green-600" />
      <div>
        <p className="font-medium">Generación en progreso</p>
        <p className="text-sm text-gray-600">
          ID de seguimiento: <code className="bg-gray-100 px-2 py-1 rounded">{trackingId}</code>
        </p>
      </div>
    </CardContent>
  </Card>
)}
```

---

## 4. Criterios de cierre

| Criterio | Verificación |
|----------|--------------|
| Clustering GEE optimizado | Candidatos GEE ≤ 3 por episodio |
| Performance mejorada en histórico | Carga inicial < 1s |
| Navegación consistente en mapa | Test E2E pasa |
| Verificar terreno funcional | Checklist visible con resultados |
| Exploración satelital sin bloqueos | Wizard completo sin redirect a login |
| Documentación alineada con UI | Grep de términos obsoletos vacío |

---

## 5. Orden de ejecución recomendado

```
SEMANA 1: Hardening + Clustering
├── Día 1-2: T4.1 (Security P0)               -> COMPLETO
├── Día 3: T7.2 (Optimización clustering)
└── Día 4-5: T7.3 (Performance histórico)

SEMANA 2: UI/UX + Bug fixes
├── Día 1: T7.1 (Documentación)
├── Día 2: T7.4 (Bug mapa)
├── Día 3-4: T7.5 (Verificar terreno)
└── Día 5: T7.6 (Ajustes exploración)

SEMANA 3: Wizard exploración
├── Día 1-2: T5.1.1-T5.1.4 (Backend Celery)   -> COMPLETO
├── Día 3-4: T5.1.5-T5.1.8 (Frontend wizard)  -> COMPLETO
└── Día 5: Integración y testing

SEMANA 4: Testing y cierre
├── Día 1-2: T6.1 (Tests unitarios)
├── Día 3: T6.2 (Tests integración)
├── Día 4: T6.3 (Tests E2E)
└── Día 5: T6.4 (Monitoreo) + Deploy
```

---

## 6. Archivos de referencia

| Archivo | Propósito |
|---------|-----------|
| `/mnt/project/2_casos_de_uso_final.md` | Casos de uso a actualizar |
| `/mnt/project/workers_documentation.md` | Documentación de workers Celery |
| `/mnt/project/UC_F08R_technical_task.md` | Especificación de clustering |
| `/mnt/project/endpoints_tasks.md` | Tareas de endpoints pendientes |
| `/mnt/user-data/uploads/adjustments.md` | Ajustes propuestos (input) |

---

## 7. Instrucciones finales para el agente

1. **Leer este documento completo** antes de iniciar
2. **Priorizar T7.2** (clustering) ya que reduce costos GEE
3. **Crear branch por fase:** `feature/fase-7-ui-ux`
4. **Commits atómicos:** `T7.2.1: analyze clustering algorithm`
5. **No modificar endpoints existentes** sin verificar contratos
6. **Preguntar** ante cualquier ambigüedad

---

*— Fin del documento —*
