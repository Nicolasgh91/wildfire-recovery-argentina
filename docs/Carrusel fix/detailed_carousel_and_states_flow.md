# 🔄 Flujo de Trabajo: Episodios de Fuego y Carrusel de Imágenes

Este documento detalla el ciclo de vida completo de los *Fire Events* y *Fire Episodes*, las inconsistencias encontradas en la lógica temporal, la propuesta de solución basada en parámetros del sistema editables, y el funcionamiento exacto del carrusel de imágenes satelitales (GEE).

---

## 1. Ciclo de Vida y Estados (*States*)

### 1.1 El GAP (Problema Encontrado)
Actualmente, el código tiene lógicas temporales asimétricas ("hardcodeadas" en los defaults) que confunden la vida de un Evento individual con la de un Episodio:
- **Eventos:** Esperan **7 días** sin calor activo para pasar de [monitoring](file:///c:/Users/nicog/wildfire-recovery-argentina/app/services/fire_service.py#131-138) a `extinct`.
- **Episodios:** Representan una agrupación de eventos. Sin embargo, la rutina de agrupación fuerza el estado del episodio a `extinct` si este no suma un *nuevo* evento en **solo 4 días**.
- **Resultado:** Eventos que duran 7 días en monitoreo quedan asociados a un episodio que se declaró `extinct` prematuramente a los 4 días. El carrusel ignora episodios extintos.

### 1.2 Estados Propuestos (Diferenciando Evento vs Episodio)

Es imperativo entender que **un evento no comparte el mismo estado con un episodio**. 

Para permitir el monitoreo satelital a largo plazo (evaluación de cicatrices), se establecen las siguientes reglas estrictas para los **Episodios**:

| Estado de Episodio | Definición y Criterios Transicionales | Acción del Sistema |
|---|---|---|
| 🟢 **[active](file:///c:/Users/nicog/wildfire-recovery-argentina/app/services/fire_service.py#761-809)** | El episodio tiene **al menos 1 evento** asociado en estado [active](file:///c:/Users/nicog/wildfire-recovery-argentina/app/services/fire_service.py#761-809). | Visible en el mapa como "Activos". Alta prioridad para buscar imágenes en GEE. |
| 🟡 **[monitoring](file:///c:/Users/nicog/wildfire-recovery-argentina/app/services/fire_service.py#131-138)** | **Todos** los eventos internos del episodio pasaron a [monitoring](file:///c:/Users/nicog/wildfire-recovery-argentina/app/services/fire_service.py#131-138) o `extinct`. | Fuego sin calor activo pero bajo vigilancia de cicatrices y rebrotes. Es candidato principal para el carrusel GEE. |
| 🔴 **`extinct`** | El episodio **no ha tenido ningún nuevo evento** asociado y todos sus eventos internos están en estado `extinct`. | Finaliza para el monitoreo inmediato. Ya no se busca en GEE. |
| ⚪ **`closed`** | Estado técnico. | El episodio fue absorbido por otro más grande (Merge) o cerrado a mano. |

---

## 2. Parámetros del Sistema (Valores Canónicos)

La modificación temporal **no debe estar hardcodeada** en el código. El sistema ya cuenta con el módulo [episode_flow_parameters.py](file:///c:/Users/nicog/wildfire-recovery-argentina/app/services/episode_flow_parameters.py) el cual intenta leer estos valores desde la tabla de base de datos `system_parameters`.

### Propuesta de Corrección:
1. Asegurar que los siguientes registros existan en la tabla `system_parameters` de la base de datos de producción (usando un query SQL o desde un futuro panel de admin).
2. El código leerá estos valores dinámicamente. Si se desea cambiar la ventana de 30 a 60 días en el futuro, solo se toca la DB sin requerir un nuevo deploy de código.

**Valores Recomendados:**
* `event_temporal_window_hours`: **48** (2 días) - *Tiempo límite entre dos detecciones aisladas para unirlas al mismo fuego.*
* [event_monitoring_window_hours](file:///c:/Users/nicog/wildfire-recovery-argentina/app/services/fire_service.py#131-138): **720 o 1440** (30 o 60 días) - *Tiempo que el evento sobrevive en 'monitoring'.*
* `episode_temporal_window_hours`: **720 o 1440** (mismo que el anterior) - *Corrige el bug. El episodio espera 30/60 días antes de declararse extinto.*

---

## 3. Carrusel de Thumbnails (Flujo Completo)

La tarea [generate_carousel](file:///c:/Users/nicog/wildfire-recovery-argentina/workers/tasks/carousel_task.py#14-36) (ejecutada diariamente a las 00:00 ART e invocable manualmente) procesa episodios para nutrir la interfaz visual ("FireCards").

### 3.1 Criterios de Selección (Casos de uso)
El worker no procesa todos los fuegos. Filtra los episodios de la base de datos siguiendo estas reglas:
1. **Estado:** `status IN ('active', 'monitoring')` (Por esto fallaba antes).
2. **Bandera GEE:** `gee_candidate = true` (Episodios relevantes, no puntos de calor sueltos).
3. **Límite:** Trae el top `N` episodios (por defecto los principales del país), ordenados por `gee_priority` (cantidad de focos de calor) y fecha de inicio.

### 3.2 Peticiones al GEE (Cuándo, Qué y a Partir de Qué Fecha)

**Momento exacto de la petición:** 
Las peticiones a GEE no se hacen cada vez que ingresa un punto FIRMS. Se consolidan en un único proceso "Batch" diario.
1. La tarea programada (`worker-analysis: carousel-daily`) se dispara a las **03:00 UTC (00:00 ART)** todos los días.
2. También se puede disparar manualmente interactuando con la API o consola.

**Qué imagen busca y de qué fecha:**
Es crucial entender esto: **El carrusel NO usa la imagen satelital del momento en que inició el incendio**. El objetivo del carrusel es mostrar **la situación actual o lo más reciente posible** del terreno quemado (cicatrices).

Por lo tanto, por cada episodio candidato, el worker realiza **una sola petición conceptual** a Google Earth Engine buscando un cruce de **Sentinel-2** con el siguiente algoritmo:

1. Busca la imagen más despejada posible de los **últimos 7 días** a partir de "HOY", intentando buscar cruces con menos del 10% de nubes.
2. Si no hay imágenes despejadas (ej: semana de lluvia), relaja el límite a `< 20%` de nubes sobre esa misma ventana de 7 días.
3. Continúa relajando a `< 30%` y `< 50%` siempre priorizando la actualidad.
4. **Fallback de Archivo:** Si absolutamente toda la semana pasada estuvo cubierta y no hay datos útiles recientes, hace una última petición buscando la imagen más reciente (con `< 30%` nubes) retrocediendo hasta un máximo de **30 días atrás**. Esta imagen se marca en la UI como "Archivo".

> **Importante:** Se hace **solo UNA Petición de Búsqueda** por episodio activo. De esa escena base seleccionada (ej. la de ayer a la tarde sin nubes), se derivan los 3 recortes o versiones visuales (RGB, SWIR, NBR). No se hacen peticiones cruzadas de diferentes días para un mismo carrusel de episodio en ese run.

### 3.3 Imágenes Mostradas
A partir de la fecha de captura real de la imagen dictada por GEE, el sistema descarga **3 Thumbnails** HD por episodio:
1. **RGB (Color Verdadero):** Como lo vería el ojo humano. Ideal para ver humo diurno y terreno.
2. **SWIR (Infrarrojo Onda Corta):** Penetra el humo y la neblina ligera. Resalta focos de calor remanente en rojo brillante o naranja.
3. **NBR (Normalized Burn Ratio):** Índice matemático. Aplica una paleta de colores donde el negro/rojo profundo marca el suelo severamente quemado, contrastando drásticamente con la vegetación verde circundante.

### 3.4 Carga y Caché
* Las imágenes se suben al Object Storage (OCI) con la marca de agua (Logo, fecha de la pasada del satélite, y nivel de nubes).
* Se graba en la base de datos la meta data.
* **Mecanismo de Caché:** Al día siguiente, si el worker nota que Sentinel-2 *no ha vuelto a pasar* por encima de ese incendio (GGE devuelve el mismo `image_id` de ayer), la tarea dice `Cache HIT` y saltea la descarga, ahorrando dinero y cuotas. Sólo baja imágenes nuevas cuando orbitó un satélite nuevo en la zona.
