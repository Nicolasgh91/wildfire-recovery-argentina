# ForestGuard - Manual de Usuario

**Versión**: 2.0  
**Fecha de actualización**: Febrero 2026  
**Idioma**: Español (Argentina)  
**Público**: Usuario general, investigadores, profesionales

---

## 📑 Tabla de Contenidos

1. [Introducción](#1-introducción)
2. [Primeros Pasos](#2-primeros-pasos)
3. [Navegación General](#3-navegación-general)
4. [Funcionalidades Principales](#4-funcionalidades-principales)
5. [Preguntas Frecuentes](#5-preguntas-frecuentes)
6. [Resolución de Problemas](#6-resolución-de-problemas)
7. [Contacto y Soporte](#7-contacto-y-soporte)

---

## 1. Introducción

### 1.1 ¿Qué es ForestGuard?

**ForestGuard** es una plataforma de monitoreo y análisis de incendios forestales en Argentina que combina:

- 🛰️ **Imágenes satelitales** de Google Earth Engine (Sentinel-2)
- 🔥 **Detecciones de incendios** de NASA FIRMS (VIIRS/MODIS)
- 🌡️ **Datos climáticos** de Open-Meteo
- 📊 **Análisis espacial** con PostGIS y H3 spatial indexing
- ⚖️ **Validación legal** según Ley 26.815

### 1.2 ¿Para quién es ForestGuard?

ForestGuard está diseñado para:

| Perfil | Caso de Uso |
|--------|-------------|
| **Ciudadanos** | Verificar si hubo incendios en un terreno antes de comprar/arrendar |
| **Periodistas** | Investigar patrones de incendios en áreas específicas |
| **ONGs** | Analizar tendencias de recurrencia en áreas protegidas |
| **Peritos judiciales** | Generar reportes con evidencia satelital para causas legales |
| **Investigadores** | Estudiar el impacto de incendios en bosques nativos |
| **Fiscalías** | Obtener evidencia técnica para investigaciones |

### 1.3 ¿Qué puedo hacer con ForestGuard?

✅ **Consultar histórico de incendios** con filtros avanzados  
✅ **Verificar terrenos** para prohibiciones legales según Ley 26.815  
✅ **Explorar imágenes satelitales** antes/durante/después de incendios  
✅ **Generar reportes PDF** con evidencia técnica verificable  
✅ **Analizar recurrencia** en áreas de interés  
✅ **Ver estadísticas públicas** sin necesidad de registro

---

## 2. Primeros Pasos

### 2.1 Requisitos del Sistema

| Requisito | Especificación |
|-----------|----------------|
| **Navegador** | Chrome 90+, Firefox 88+, Safari 14+, Edge 90+ |
| **Conexión** | Recomendado: 5 Mbps o superior |
| **Dispositivo** | Escritorio, tablet o móvil (diseño responsive) |
| **JavaScript** | Habilitado (requerido) |

### 2.2 Registro de Cuenta

#### Paso 1: Acceder a la Landing Page

1. Ingresá a **https://forestguard.freedynamicdns.org/**
2. Verás la pantalla de bienvenida con el título **"ForestGuard"**
3. Subtítulo: *"Evidencia satelital para entender qué pasó con el territorio después de un incendio"*

#### Paso 2: Crear Cuenta

**Opción A: Registro con Email**

1. Hacé clic en **"Crear cuenta"** (debajo del formulario de login)
2. Completá el formulario:
   - **Nombre completo** (ej: Juan Pérez)
   - **Email** (ej: juan.perez@example.com)
   - **Contraseña** (mínimo 8 caracteres, incluir mayúsculas, números y símbolos)
   - **Confirmar contraseña**
3. Aceptá los **Términos y Condiciones** (checkbox obligatorio)
4. Hacé clic en **"Registrarme"**
5. Verificá tu email y hacé clic en el link de confirmación

**Opción B: Registro con Google**

1. Hacé clic en el botón **"Continuar con Google"**
2. Seleccioná tu cuenta de Google
3. Autorizá el acceso a ForestGuard
4. Serás redirigido automáticamente al dashboard

> **💡 Tip**: El registro con Google es más rápido y no requiere verificación de email.

### 2.3 Inicio de Sesión

1. Ingresá tu **email** y **contraseña**
2. (Opcional) Marcá **"Recordarme"** para mantener la sesión activa
3. Hacé clic en **"Iniciar sesión"**

**¿Olvidaste tu contraseña?**
1. Hacé clic en **"¿Olvidaste tu contraseña?"**
2. Ingresá tu email registrado
3. Recibirás un link de recuperación por email
4. Creá una nueva contraseña

---

## 3. Navegación General

### 3.1 Barra de Navegación

La barra superior contiene:

```
┌────────────────────────────────────────────────────────────────┐
│  🌳 ForestGuard  │  Inicio  │  Mapa  │  Histórico  │  [Usuario] │
└────────────────────────────────────────────────────────────────┘
```

| Elemento | Descripción |
|----------|-------------|
| **Logo ForestGuard** | Hacé clic para volver al inicio |
| **Inicio** | Dashboard principal con estadísticas |
| **Mapa** | Visualización geográfica de incendios |
| **Histórico** | Consulta filtrable de incendios pasados |
| **[Nombre Usuario]** | Menú desplegable con opciones de cuenta |

### 3.2 Menú de Usuario

Haciendo clic en tu nombre (esquina superior derecha), accedés a:

- **Mi perfil** - Ver y editar información personal
- **Verificar terreno** - Auditoría legal de uso del suelo
- **Exploración satelital** - Generar reportes con imágenes
- **Certificados** - Centro de descarga de evidencia visual
- **Configuración** - Preferencias de cuenta
- **Salir** - Cerrar sesión

### 3.3 Idioma

Actualmente disponible en **Español (Argentina)**.

> **🚧 En desarrollo**: Versión en inglés (próximo release)

---

## 4. Funcionalidades Principales

### 4.1 Dashboard (Inicio)

#### ¿Qué es?
Vista general con estadísticas y accesos rápidos a funcionalidades clave.

#### ¿Qué verás?

**KPIs Principales:**
- **Total de incendios** del último año
- **Hectáreas afectadas** (acumulado)
- **Incendios activos** (en tiempo real)
- **Promedio de duración** (en días)

**Gráficos:**
- **Serie temporal**: Incendios por mes (últimos 12 meses)
- **Distribución por provincia**: Top 5 provincias más afectadas
- **Estado de incendios**: Activos vs. Extinguidos

**Accesos Rápidos:**
- 📍 **Verificar terreno** → Botón destacado
- 🛰️ **Explorar imágenes** → Acceso a exploración satelital
- 📊 **Ver mapa** → Visualización geográfica

#### ¿Cómo usarlo?

1. **Ver estadísticas generales**: Los KPIs se actualizan automáticamente
2. **Filtrar por fecha**: Usá el selector de rango de fechas (esquina superior)
3. **Hacer clic en "Ver más"** para detalles de cada gráfico

---

### 4.2 Mapa de Incendios

#### ¿Qué es?
Visualización geográfica interactiva de todos los incendios detectados en Argentina.

#### Capas del Mapa

| Capa | Descripción | Toggle |
|------|-------------|--------|
| **Incendios activos** | Marcadores rojos pulsantes | ✅ Por defecto |
| **Incendios extinguidos** | Marcadores grises | ⬜ Opcional |
| **Áreas protegidas** | Polígonos verdes | ⬜ Opcional |
| **Heat map** | Densidad de incendios | ⬜ Opcional |

#### Controles

```
┌───────────────────────────────────────────┐
│  [Buscar ubicación...]                    │
│  ┌──────────────────────────────────────┐ │
│  │                                      │ │
│  │          🗺️ MAPA INTERACTIVO        │ │
│  │                                      │ │
│  └──────────────────────────────────────┘ │
│  [− Zoom +]  [🏠 Centrar]  [🔍 Filtros]  │
└───────────────────────────────────────────┘
```

**Controles disponibles:**
- **Zoom**: Rueda del mouse o botones +/-
- **Pan**: Clic y arrastrá para mover el mapa
- **Buscar**: Ingresá una provincia, ciudad o dirección
- **Filtros**: Rango de fechas, provincia, estado

#### ¿Cómo usarlo?

**Ver detalles de un incendio:**
1. Hacé clic en un marcador del mapa
2. Se abrirá un popup con:
   - Nombre del incendio
   - Fecha de inicio
   - Estado actual
   - Hectáreas afectadas
   - FRP (Fire Radiative Power) máximo
3. Hacé clic en **"Ver detalles"** para info completa

**Filtrar incendios:**
1. Hacé clic en el botón **"Filtros"** (esquina superior derecha)
2. Seleccioná criterios:
   - **Rango de fechas** (ej: últimos 30 días)
   - **Provincia** (ej: Córdoba)
   - **Estado** (activo, extinguido, contenido)
3. Hacé clic en **"Aplicar"**
4. El mapa se actualizará automáticamente

**Activar capas:**
1. Hacé clic en el ícono de capas (🗂️)
2. Marcá/desmarcá las capas deseadas
3. Los cambios se aplican en tiempo real

---

### 4.3 Histórico de Incendios

#### ¿Qué es?
Tabla filtrable con todos los incendios registrados, con opciones de búsqueda, ordenamiento y exportación.

#### Columnas de la Tabla

| Columna | Descripción |
|---------|-------------|
| **Nombre** | Identificación del incendio (auto-generado) |
| **Provincia** | Ubicación geográfica |
| **Fecha inicio** | Primer detección satelital |
| **Fecha fin** | Última detección o extinción confirmada |
| **Estado** | Activo / Extinguido / Contenido |
| **Área (ha)** | Hectáreas afectadas estimadas |
| **FRP máx** | Fire Radiative Power máximo (MW) |
| **Acciones** | Botones: Ver detalles, Descargar reporte |

#### Filtros Disponibles

**Búsqueda por texto:**
- Ingresá nombre de provincia, localidad o ID de incendio
- Búsqueda en tiempo real (actualiza mientras escribís)

**Filtros avanzados:**
1. **Rango de fechas**: Calendario con inicio y fin
2. **Provincia**: Dropdown con todas las provincias
3. **Estado**: Multi-select (activo, extinguido, contenido)
4. **Área mínima**: Solo incendios > X hectáreas
5. **En área protegida**: Checkbox para filtrar solo áreas protegidas

#### ¿Cómo usarlo?

**Buscar un incendio específico:**
1. Usá la barra de búsqueda (ícono 🔍)
2. Ingresá: provincia, fecha aproximada o ID
3. La tabla se filtra automáticamente

**Ordenar resultados:**
1. Hacé clic en el encabezado de cualquier columna
2. Primera vez: orden ascendente (↑)
3. Segunda vez: orden descendente (↓)
4. Tercera vez: vuelve al orden original

**Exportar datos:**
1. Aplicá los filtros deseados
2. Hacé clic en **"Exportar"** (esquina superior derecha)
3. Seleccioná formato:
   - **CSV** (Excel, Google Sheets)
   - **JSON** (programación, APIs)
4. Máximo: 10,000 registros por exportación

**Paginación:**
- Resultados por página: 20 (default), 50, 100
- Navegación: ◀ Anterior | 1 2 3 ... | Siguiente ▶

---

### 4.4 Verificar Terreno (Auditoría Legal)

#### ¿Qué es?
Herramienta para investigar si hubo incendios en un terreno y determinar prohibiciones legales según **Ley 26.815**.

> **⚖️ Marco Legal**: La Ley 26.815 prohíbe el cambio de uso del suelo por **60 años** en bosques nativos y **30 años** en zonas agrícolas tras un incendio.

#### Flujo de Uso

**Paso 1: Buscar el Lugar**

Tres formas de buscar:
1. **Por dirección**: Ej: "Av. Córdoba 1200, CABA"
2. **Por localidad**: Ej: "Villa Carlos Paz, Córdoba"
3. **Por parque nacional**: Ej: "Parque Nacional Quebrada del Condorito"
4. **Marcar en el mapa**: Clic directo en el mapa interactivo

**Paso 2: Definir Área de Análisis**

Seleccioná el radio de búsqueda con chips predefinidos:

| Opción | Radio | Uso recomendado |
|--------|-------|-----------------|
| **Alrededores** | 500 m | Terreno pequeño, lote urbano |
| **Zona** | 1 km | Campo mediano, zona rural |
| **Amplio** | 3 km | Campo grande, análisis regional |
| **Personalizado** | Manual | Avanzado (en "Opciones Avanzadas") |

**Paso 3: Opciones Avanzadas (opcional)**

Hacé clic en **"Opciones Avanzadas"** para:
- Ajustar coordenadas exactas (lat/lon decimal)
- Ingresar ID catastral (si lo conocés)
- Radio personalizado (hasta 5000 m)

**Paso 4: Verificar**

1. Hacé clic en **"Verificá"** (botón principal verde)
2. Se muestra checklist de verificación:
   - ✅ ¿Hubo incendios en los últimos años en esta zona?
   - ✅ ¿La vegetación se recuperó o quedó degradada?
   - ✅ ¿Persisten señales del incendio en el área?
   - ✅ ¿Qué dicen fuentes públicas y registros locales?
3. Estado de carga: "Buscando incendios..." → "Analizando área protegida..." → Resultados

#### Resultados

**Si NO hay incendios:**
```
✅ No se encontraron incendios en el área analizada
   Radio: 1 km desde lat -31.42, lon -64.18
   Período analizado: últimos 10 años
```

**Si HAY incendios:**

```
⚠️ Se encontraron 2 incendios en el área

┌──────────────────────────────────────────────────────────────┐
│ Incendio 1: Sierras Chicas                                   │
│ • Fecha: 15 de marzo de 2024                                 │
│ • Distancia: 450 m del punto de consulta                     │
│ • Área protegida: Parque Nacional Quebrada del Condorito     │
│ • Prohibición hasta: 15 de marzo de 2084 (60 años)           │
│ • Evidencia visual: [Ver thumbnail satelital]                │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ Incendio 2: Los Gigantes                                     │
│ • Fecha: 8 de enero de 2023                                  │
│ • Distancia: 1.2 km                                          │
│ • Categoría: Zona agrícola                                   │
│ • Prohibición hasta: 8 de enero de 2053 (30 años)            │
└──────────────────────────────────────────────────────────────┘
```

**Descarga de Reporte:**
- Hacé clic en **"Descargar reporte PDF"**
- El PDF incluye:
  - Hash SHA-256 para verificación
  - Mapa con ubicación del terreno y perímetros de incendios
  - Imágenes satelitales (thumbnails)
  - Fuentes de datos utilizadas
  - Disclaimer legal

#### Interpretación de Resultados

> **⚠️ Importante**: Esta herramienta provee evidencia técnica para investigación. **NO constituye asesoramiento legal**. Consultá con un abogado especializado para decisiones legales o contractuales.

**Microcopy guiado:**
- *"Algunos incendios son accidentales; otros pueden tener intereses detrás. Acá podés mirar evidencia y sacar tus conclusiones."*
- *"Esto no demuestra intencionalidad por sí solo. Sirve para contrastar relatos con evidencia observable."*

---

### 4.5 Exploración Satelital

#### ¿Qué es?
Wizard de 6 pasos para observar, comparar y comprender cambios en el terreno afectado por incendios usando imágenes satelitales HD.

> **💰 Costo**: Cada imagen HD solicitada tiene un costo de **U$D 0.50** (1 crédito). La transparencia de costos se muestra **antes** de procesar.

#### Tipos de Reporte

| Tipo | Descripción | Público | Max Imágenes |
|------|-------------|---------|--------------|
| **Histórico** | Análisis de recuperación post-incendio | General | 12 |
| **Judicial** | Evidencia técnica para causas legales | Peritos, fiscales | Ilimitado |

#### Flujo del Wizard

**Paso 1: Búsqueda del Incendio**

1. Usá el **autocomplete** para buscar por:
   - Provincia (ej: "Córdoba")
   - Rango de fechas (ej: "enero 2024")
   - Nombre del incendio
2. Seleccioná el incendio de la lista

**Paso 2: Configuración del Reporte**

Definí los parámetros:

| Parámetro | Opciones | Descripción |
|-----------|----------|-------------|
| **Tipo** | Histórico / Judicial | Según tu necesidad |
| **Rango temporal** | Antes y después del incendio | Selector de fechas |
| **N° de imágenes** | 1 - 12 (histórico) | Frecuencia: semanal, quincenal, mensual |
| **Visualizaciones** | NDVI, NBR, SWIR, RGB | Multi-select |

**Visualizaciones disponibles:**
- **RGB**: Color natural (como una foto)
- **SWIR**: Short-Wave Infrared (destaca incendios activos)
- **NDVI**: Normalized Difference Vegetation Index (salud de vegetación)
- **NBR**: Normalized Burn Ratio (severidad del incendio)

**Paso 3: Preview y Costeo**

El sistema muestra:

```
┌──────────────────────────────────────────────────────────────┐
│ RESUMEN DE TU EXPLORACIÓN                                    │
│                                                              │
│ Incendio: Sierras Chicas                                     │
│ Período: 1 de marzo - 1 de junio de 2024                    │
│                                                              │
│ 📸 Imágenes a generar: 12                                    │
│ 🎨 Visualizaciones: NDVI, NBR, RGB (× 3 por fecha)          │
│ 💰 Costo total: U$D 6.00 (12 créditos)                      │
│ ⏱️ Tiempo estimado: 90 segundos                              │
│                                                              │
│ [◀ Volver] [Confirmar y Pagar ✓]                            │
└──────────────────────────────────────────────────────────────┘
```

**Paso 4: Confirmación y Pago**

1. Revisá el resumen
2. Hacé clic en **"Confirmar y Pagar"**
3. Serás redirigido a **MercadoPago**
4. Completá el pago (tarjeta, MercadoPago cuenta, efectivo)
5. Volvés automáticamente a ForestGuard

**Paso 5: Generación (Polling)**

Estado visible en tiempo real:

```
🔄 Generando tu reporte...

✅ Buscando imágenes satelitales      [████████] 100%
🔄 Procesando visualizaciones         [███░░░░░]  40%
⏳ Generando PDF                      [░░░░░░░░]   0%

Progreso: 47% completado
Tiempo restante estimado: 53 segundos
```

**Paso 6: Descarga**

Una vez completado:

```
✅ ¡Tu exploración está lista!

📄 Reporte: sierras_chicas_2024.pdf (12.4 MB)
🔐 Hash SHA-256: abc123def456...
📅 Generado: 9 de febrero de 2026, 18:45 UTC
⏰ Disponible por: 90 días

[Descargar PDF ⬇]  [Verificar Hash 🔍]  [Nueva Exploración +]
```

#### Contenido del PDF

El reporte incluye:

1. **Portada** con logo ForestGuard + watermark
2. **Resumen ejecutivo**: Datos del incendio, área afectada, severidad
3. **Cronología temporal**: Timeline de eventos clave
4. **Comparaciones visuales**:
   - Before/After con slider
   - Serie temporal NDVI (gráfico)
   - Mapa de severidad (dNBR)
5. **Imágenes HD** seleccionadas (12 páginas)
6. **Metadata técnica**:
   - Fuentes de datos (NASA FIRMS, Sentinel-2, Open-Meteo)
   - GEE system index (reproducibilidad)
   - Cobertura de nubes por imagen
7. **Disclaimers y limitaciones**
8. **QR code** para verificación pública
9. **Hash SHA-256** del documento completo

#### Verificación del Hash

Para verificar la autenticidad:

1. Copiá el hash del PDF
2. Ingresá a **https://forestguard.freedynamicdns.org/verify/[hash]**
3. O escaneá el QR code del PDF
4. Verás confirmación: ✅ "Documento válido, generado el [fecha]"

---

### 4.6 Certificados (Centro de Exploración Visual)

#### ¿Qué es?
Centro de descarga de evidencia satelital con hasta **12 imágenes full HD** seleccionables para investigación y concientización.

> **🎯 Enfoque**: Curiosidad e investigación educativa (no certificados legales con firma digital)

#### Diferencia con Exploración Satelital

| Aspecto | Certificados | Exploración Satelital |
|---------|--------------|------------------------|
| **Enfoque** | Educativo, visual | Técnico, profesional |
| **Límite imágenes** | 12 máximo | 12 (histórico) / ilimitado (judicial) |
| **Output** | PDF personalizable | PDF técnico con metadata completa |
| **Costo** | Por definir | U$D 0.50/imagen |
| **Narrativa** | "Ver con tus propios ojos" | "Evidencia verificable" |

#### Flujo de 4 Pasos

**Paso 1: Selección del Área**

1. Buscá lugar por dirección, localidad o parque
2. O marcá directamente en el mapa interactivo
3. Definí perímetro de análisis (polígono o radio)

**Paso 2: Selección de Fechas/Imágenes**

```
┌──────────────────────────────────────────────────────────────┐
│ TIMELINE DE IMÁGENES                                         │
│                                                              │
│ Pre-incendio    Durante    Post 3 meses    Post 1 año       │
│     ●──────────── ● ─────────── ● ────────────── ●          │
│   📅 Mar 1     Mar 15      Jun 15         Mar 15 +1         │
│                                                              │
│ Imágenes seleccionadas: 8 de 12                             │
│                                                              │
│ [Thumbnails clickeables con multi-select]                   │
│ [✓] Mar 1  [✓] Mar 15  [✓] Mar 20  [ ] Abr 1  [✓] Abr 15   │
└──────────────────────────────────────────────────────────────┘
```

**Timeline con hitos predefinidos:**
- **Pre-incendio** (7-15 días antes)
- **Durante** (fecha de detección)
- **Post 3 meses** (recuperación temprana)
- **Post 1 año** (recuperación a largo plazo)

**Paso 3: Vista Previa y Resumen**

**Comparador Before/After:**
```
┌────────────────────────────────────────────┐
│  ANTES (1 Mar)      │  DESPUÉS (15 Jun)    │
│                     │                      │
│  [Imagen satelital] │  [Imagen satelital]  │
│   Vegetación densa  │  Área quemada        │
│                     │                      │
│  ← Deslizá para comparar →                 │
└────────────────────────────────────────────┘
```

**Qué incluye tu PDF:**
- ✅ 8 imágenes full HD seleccionadas
- ✅ Comparación temporal (antes/durante/después)
- ✅ Indicadores por imagen:
  - 🌿 Vegetación saludable (NDVI alto)
  - 💧 Estrés hídrico (NDVI bajo)
  - 🔥 Cicatriz del incendio (dNBR)
- ✅ Fuentes transparentes (NASA, ESA, Google)
- ✅ Limitaciones conocidas (nubosidad, resolución)

**Paso 4: Generación y Descarga**

1. Hacé clic en **"Generar mi PDF"**
2. El documento se arma con lo que elegiste
3. Descarga disponible en 60-90 segundos

#### PDF Personalizable

El reporte cuenta una **historia visual**:

1. **Intro**: "Qué pasó en [nombre del área]"
2. **Contexto**: Ubicación, fechas clave, área afectada
3. **Viaje temporal**:
   - "Antes del incendio" (imagen + descripción)
   - "Durante el incendio" (imagen + SWIR destacando fuego)
   - "3 meses después" (imagen + NDVI mostrando recuperación)
   - "1 año después" (imagen + comparación final)
4. **Indicadores traducidos**:
   - 🌿 "Vegetación saludable" en vez de "NDVI 0.8"
   - 💧 "Humedad del suelo" en vez de "SM %"
   - 🔥 "Severidad del daño" en vez de "dNBR class"
5. **Fuentes y limitaciones** en lenguaje simple

#### Micro-momentos de Aprendizaje

**Tooltips en la interfaz:**
- Hover sobre "NDVI" → "Mide qué tan verde y saludable está la vegetación"
- Hover sobre "dNBR" → "Indica cuánto daño causó el incendio (del 1 al 10)"
- Hover sobre "Sentinel-2" → "Satélite europeo que toma fotos de la Tierra cada 5 días"

**Etiquetas con significado humano:**
- ❌ "SWIR Band 12, 2190nm"
- ✅ "Infrarrojo para ver fuego activo"

---

### 4.7 Mi Perfil

#### ¿Qué puedo hacer?

**Información Personal:**
- Ver y editar nombre completo
- Cambiar email (requiere re-verificación)
- Actualizar contraseña
- Cambiar foto de perfil (opcional)

**Créditos (si aplica):**
- Ver saldo actual de créditos
- Historial de consumo
- Recargar créditos (MercadoPago)

**Historial de Actividad:**
- Auditorías de terreno realizadas
- Exploraciones satelitales generadas
- Certificados descargados

**Seguridad:**
- Activar autenticación de dos factores (2FA)
- Ver dispositivos conectados
- Cerrar sesiones activas

---

## 5. Preguntas Frecuentes

### 5.1 Sobre los Datos

**¿De dónde vienen los datos de incendios?**

Los datos provienen de múltiples fuentes confiables:
- **NASA FIRMS**: Detecciones de incendios vía satélites VIIRS y MODIS (resolución 375m y 1km)
- **Sentinel-2**: Imágenes ópticas de alta resolución (10-20m) de la Agencia Espacial Europea
- **Open-Meteo**: Datos climáticos (temperatura, humedad, viento)
- **Datos oficiales**: Áreas protegidas de Argentina (Administración de Parques Nacionales)

**¿Cada cuánto se actualizan los datos?**

- **Detecciones de incendios**: Cada 6-12 horas (según disponibilidad de NASA FIRMS)
- **Imágenes satelitales**: Nuevas imágenes cada 5 días (Sentinel-2)
- **Estadísticas públicas**: Actualización diaria a las 02:00 UTC
- **Carrusel de incendios activos**: Generación diaria a las 01:00 UTC

**¿Qué tan precisos son los datos?**

Cada incendio tiene un **Reliability Score** (0-100) basado en:
- Confianza de detecciones satelitales (40%)
- Calidad de imágenes (20%)
- Datos climáticos disponibles (20%)
- Detecciones independientes (20%)

Clasificación:
- **High** (≥ 80): Datos de alta confianza
- **Medium** (50-79): Confianza moderada
- **Low** (< 50): Datos limitados, verificar con fuentes adicionales

### 5.2 Sobre la Ley 26.815

**¿Qué es la Ley 26.815?**

Ley Nacional de Manejo del Fuego que establece:
> *"Se prohíbe por 60 años el cambio de uso del suelo en áreas de bosques nativos o áreas protegidas afectadas por incendios. En zonas agrícolas y praderas, la prohibición es de 30 años."*

**¿Las fechas de prohibición son oficiales?**

ForestGuard calcula las fechas **automáticamente** basándose en:
1. Fecha del incendio (detección satelital)
2. Ubicación (cruce con áreas protegidas)
3. Categoría legal (bosque nativo vs. zona agrícola)

> **⚠️ Importante**: Estas fechas son **indicativas**. Para documentación oficial, consultá con la autoridad de aplicación de tu provincia.

**¿Puedo usar el reporte de ForestGuard en trámites legales?**

Sí, nuestros reportes incluyen:
- ✅ Hash SHA-256 verificable
- ✅ QR code de autenticación
- ✅ Fuentes de datos transparentes
- ✅ Metadata técnica reproducible

Sin embargo, **recomendamos** complementar con:
- Peritaje técnico oficial
- Consulta a escribano o abogado especializado
- Verificación con autoridades de aplicación locales

### 5.3 Sobre Costos y Pagos

**¿ForestGuard es gratis?**

Funcionalidades **gratuitas** (sin registro):
- Ver estadísticas públicas
- Explorar mapa de incendios
- Consultar histórico básico

Funcionalidades **gratuitas** (con registro):
- Dashboard completo con filtros
- Verificar terrenos (auditoría legal)
- Descargar reportes básicos (thumbnails)

Funcionalidades **pagas**:
- Exploración satelital con imágenes HD: **U$D 0.50 por imagen**
- Reportes judiciales ilimitados: Según cantidad de imágenes

**¿Cómo se paga?**

Aceptamos pagos vía **MercadoPago**:
- Tarjetas de crédito/débito
- MercadoPago cuenta
- Efectivo (Rapipago, Pago Fácil)

**Sistema de créditos:**
- 1 crédito = U$D 0.50
- 1 imagen HD = 1 crédito
- Podés comprar packs: 10, 20, 50, 100 créditos

**¿Hay reembolsos?**

Sí, podés solicitar reembolso hasta **24 horas** después de la compra si:
- No descargaste el PDF generado
- Hubo un error técnico en la generación

### 5.4 Sobre Privacidad y Seguridad

**¿Qué datos recopila ForestGuard?**

Recopilamos:
- Email y nombre (registro)
- Historial de búsquedas y consultas
- Reportes generados
- Logs de auditoría de terrenos (requerido legalmente)

**NO** recopilamos:
- Ubicación en tiempo real
- Datos biométricos
- Información sensible no relacionada con el servicio

**¿Mis consultas son privadas?**

Sí. Solo vos y administradores de ForestGuard pueden ver tu historial.

**Excepción**: Los `land_use_audits` (verificación de terrenos) se registran en logs inmutables por **compliance legal** (Ley 26.815), pero sin información personal identificable.

**¿Puedo eliminar mi cuenta?**

Sí, podés solicitar la eliminación de tu cuenta desde:
1. **Mi Perfil** → **Configuración** → **Eliminar cuenta**
2. Confirmar con contraseña
3. Tus datos personales se eliminan en **30 días**

> **Nota**: Los audit logs se mantienen por requerimientos legales, pero anonimizados (sin email ni nombre).

---

## 6. Resolución de Problemas

### 6.1 No puedo iniciar sesión

**Problema**: "Email o contraseña incorrectos"

**Soluciones:**
1. Verificá que tu email esté escrito correctamente
2. Revisá si activaste tu cuenta por email (chequeá spam)
3. Usá **"¿Olvidaste tu contraseña?"** para recuperar acceso
4. Si registraste con Google, usá el botón **"Continuar con Google"**

**Problema**: "Cuenta no verificada"

**Soluciones:**
1. Buscá el email de verificación en tu bandeja de entrada
2. Chequeá la carpeta de **Spam** o **Promociones**
3. Hacé clic en **"Reenviar email de verificación"** en la pantalla de login

### 6.2 El mapa no carga

**Problema**: Pantalla en blanco o mapa sin marcadores

**Soluciones:**
1. **Verificá tu conexión a Internet**
2. **Desactivá bloqueadores de scripts** (AdBlock, uBlock)
3. **Refrescá la página** (F5 o Ctrl+R)
4. **Limpiá caché del navegador**:
   - Chrome: Ctrl+Shift+Del → "Imágenes y archivos en caché"
5. **Probá en navegador privado/incógnito**

### 6.3 La exportación CSV falla

**Problema**: "Error al exportar datos" o archivo vacío

**Soluciones:**
1. **Reducí el rango de fechas** (máximo 10,000 registros)
2. **Aplicá más filtros** para limitar resultados
3. **Intentá exportar en JSON** en lugar de CSV
4. Si persiste, **contactá soporte** con:
   - Filtros aplicados
   - Número de registros estimados
   - Mensaje de error exacto

### 6.4 La generación de reporte demora mucho

**Problema**: "Procesando..." por más de 5 minutos

**Tiempos normales:**
- Reporte histórico (12 imágenes): 60-120 segundos
- Reporte judicial (30+ imágenes): 3-5 minutos

**Si excede el tiempo:**
1. **No cierres la pestaña** (el proceso sigue en background)
2. Esperá hasta 10 minutos (puede haber congestión de GEE)
3. Si muestra "Error", verificá:
   - Tu conexión a Internet no se cortó
   - Tenés créditos suficientes
4. Contactá soporte con el `investigation_id` (aparece en la URL)

### 6.5 Hash de verificación no coincide

**Problema**: Al verificar el hash del PDF, dice "No válido"

**Causas posibles:**
1. **El PDF fue modificado** (editado, anotado, comprimido)
2. **Copiaste el hash incorrectamente** (con espacios o caracteres extra)
3. **El archivo se corrompió** durante la descarga

**Soluciones:**
1. **Re-descargá el PDF** desde tu historial en ForestGuard
2. **No edites el PDF** antes de verificar el hash
3. **Copiá el hash completo** (64 caracteres hexadecimales)
4. Usá el **QR code** del PDF para verificación automática

---

## 7. Contacto y Soporte

### 7.1 Formulario de Contacto

**Acceso**: Desde el footer del sitio → **"Contacto"**

**Formulario:**
- Nombre completo
- Email
- Asunto (dropdown con categorías)
- Mensaje (descripción detallada)
- Adjunto (opcional, max 5 MB: .jpg, .png, .pdf)

**Categorías de asunto:**
- 💡 Consulta general
- 🐛 Reportar un error
- 💳 Problema con pagos
- 🔒 Seguridad y privacidad
- 🌟 Sugerencia de mejora

**Tiempo de respuesta:** 24-48 horas hábiles

### 7.2 Preguntas Técnicas (GitHub)

Para desarrolladores y usuarios avanzados:

**GitHub Issues**: https://github.com/[usuario]/forestguard/issues

Ideal para:
- Reportar bugs con logs técnicos
- Solicitar nuevas funcionalidades
- Contribuir con código

### 7.3 Comunidad y Redes Sociales

- **Twitter/X**: @ForestGuardArg (actualizaciones, incidencias)
- **LinkedIn**: ForestGuard (casos de uso, testimonios)
- **Email**: soporte@forestguard.app

---

## 📚 Glosario de Términos

| Término | Significado |
|---------|-------------|
| **FRP** | Fire Radiative Power - Poder radiativo del fuego en megawatts (MW). A mayor FRP, mayor intensidad del incendio. |
| **NDVI** | Normalized Difference Vegetation Index - Índice que mide la salud de la vegetación (0 = sin vegetación, 1 = vegetación densa y saludable). |
| **NBR** | Normalized Burn Ratio - Ratio que identifica áreas quemadas y su severidad. |
| **dNBR** | Difference NBR - Diferencia de NBR antes y después del incendio para medir severidad del daño. |
| **SWIR** | Short-Wave Infrared - Banda infrarroja que permite ver incendios activos y atravesar humo. |
| **GEE** | Google Earth Engine - Plataforma de análisis geoespacial de Google. |
| **Sentinel-2** | Satélite de observación terrestre de la Agencia Espacial Europea (resolución 10-20m). |
| **VIIRS/MODIS** | Instrumentos satelitales de NASA para detectar incendios (resolución 375m y 1km). |
| **PostGIS** | Extensión de PostgreSQL para datos geoespaciales. |
| **H3** | Sistema de indexación espacial hexagonal de Uber. |
| **RLS** | Row Level Security - Seguridad a nivel de fila en base de datos. |
| **Hash SHA-256** | Firma criptográfica de 256 bits que verifica integridad de documentos. |

---

**Fin del Manual de Usuario v2.0**

Para más información, visitá: **https://forestguard.freedynamicdns.org/**

*Última actualización: Febrero 2026*
