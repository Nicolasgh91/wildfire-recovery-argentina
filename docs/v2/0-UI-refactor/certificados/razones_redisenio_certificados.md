# Razones y objetivos de la mejora de ui/ux en la página de certificados

## Contexto y cambio de enfoque del producto

La página de **Certificados** evolucionó desde una idea interpretada como “certificado legal” hacia un objetivo mucho más claro y valioso para el público general: **un centro de exploración visual y descarga de evidencia satelital**.

En términos prácticos, la página pasa a ser un flujo guiado para que cualquier persona (sin conocimientos técnicos) pueda:

- **Seleccionar hasta 12 imágenes full HD** de un área afectada por incendios.
- Comparar el **antes**, el **durante** y el **después** (meses/años posteriores) para “ver con sus propios ojos” qué ocurrió.
- Descargar un **PDF** con las imágenes elegidas y un **reporte integral** (clima, vegetación, uso del suelo y otros indicadores disponibles) por cada imagen.

> Resultado deseado: que el usuario se convierta en investigador amateur por unos minutos, con herramientas claras, visuales y confiables.

---

## Problema que resuelve la mejora de ui/ux

La interfaz anterior (o el estado actual sin narrativa) tiende a comunicar:

- Una experiencia “administrativa” (parecida a trámites).
- Un lenguaje orientado a validación de autenticidad, no a exploración.
- Poca motivación para navegar, comparar y aprender.

Para un público no técnico, eso genera fricción: **no se entiende rápidamente qué se puede hacer, por qué es interesante y qué se obtiene al final**.

---

## Objetivos de la mejora

### Objetivo 1: hacer la propuesta entendible en 10 segundos
La nueva interfaz prioriza que el usuario entienda de inmediato:

- Qué va a obtener (imágenes + PDF con análisis).
- Para qué sirve (validar cambios en el terreno, aprender, concientizar).
- Qué pasos siguen (seleccionar → comparar → descargar).

### Objetivo 2: convertir la página en una experiencia de “curiosidad guiada”
Se busca introducir micro-momentos de aprendizaje:

- Explicaciones cortas (tooltips / “¿qué estoy viendo?”).
- Etiquetas con significado humano (ej.: “vegetación saludable”, “estrés hídrico”, “cicatriz del incendio”).
- Comparaciones visuales simples antes/después.

### Objetivo 3: aumentar confianza, sin exigir conocimiento técnico
La UI debe transmitir que los datos son:

- Reproducibles y consistentes (misma área, misma escala, misma fuente).
- Explicables (no “magia”, sino indicadores interpretables).
- Exportables (PDF claro y compartible).

Esto se alinea con principios del sistema como reproducibilidad y trazabilidad de resultados. :contentReference[oaicite:0]{index=0}

### Objetivo 4: mantener eficiencia y sostenibilidad (costos y performance)
La interfaz tiene que ser honesta con el rendimiento y costos del procesamiento de imágenes HD:

- Previsualización liviana primero (thumbnails / baja resolución).
- Descarga HD y PDF como acción deliberada (on-demand).
- Flujo asincrónico con estados claros (generando / listo / error).

Este enfoque está alineado con principios de arquitectura y operación (async-first, generación HD bajo demanda). :contentReference[oaicite:1]{index=1}

---

## Principios de diseño aplicados

### 1) Narrativa primero, controles después
La página debe sentirse como una “misión” simple, no como un formulario.

- Encabezado con promesa clara (qué vas a descubrir).
- Subtítulo orientado a curiosidad (“observá la evolución del terreno”).
- Pasos visibles (1. elegí área, 2. seleccioná fechas/imágenes, 3. generá tu informe).

### 2) Lenguaje humano y visual
Se evita jerga (“índice”, “reflectancia”, “bandas”) como texto principal.

- Se traduce a conceptos: “vegetación”, “humedad”, “cambios en el suelo”.
- Lo técnico queda como “ver detalle” o tooltip para quien quiera profundizar.

### 3) Comparación como mecánica central
La UI se optimiza para comparar:

- Antes / después con un control tipo slider.
- Línea de tiempo con hitos (“pre-incendio”, “post 3 meses”, “post 1 año”).
- Selección de hasta 12 imágenes con feedback inmediato (“8 de 12 seleccionadas”).

### 4) Confianza por transparencia
La interfaz comunica límites y calidad sin asustar:

- “Fuentes utilizadas” (logos y breve descripción).
- “Qué incluye el PDF” (lista simple).
- “Qué puede variar” (nubosidad, disponibilidad de escena, etc.).

---

## Qué cambia concretamente con la ui/ux mejorada

### Cambio 1: de “verificar certificado” a “explorar evidencia”
El copy y la estructura dejan de centrarse en autenticidad/trámite y pasan a:

- Explorar cambios.
- Seleccionar evidencia.
- Generar informe.

### Cambio 2: de pantalla estática a flujo guiado
Se introduce un flujo con estados:

1. Selección del área (buscar lugar / marcar en mapa).
2. Selección de fechas/imágenes (máximo 12).
3. Vista previa y resumen del informe.
4. Generación y descarga del PDF.

### Cambio 3: de output único a “informe personalizable”
El PDF deja de ser un “resultado fijo” y pasa a ser:

- Un reporte armado con lo que el usuario eligió.
- Un documento que cuenta una historia (antes/durante/después) y adjunta indicadores.

---

## Impacto esperado

### En usuarios finales
- Mayor comprensión del valor de la plataforma.
- Más tiempo explorando (no solo “entré y salí”).
- Más descargas compartibles (PDF) para conversación, educación y concientización.

### En el producto
- Mayor adopción orgánica: el usuario entiende y recomienda.
- Mejor conversión a acciones “premium” (si aplica) porque el valor es tangible.
- Datos de uso más claros para iterar (qué indicadores interesan, qué rangos temporales se eligen).

---

## Métricas para validar el éxito

- Tasa de inicio de flujo: % que pasa de la landing del módulo a seleccionar un área.
- Tasa de selección: % que elige ≥ 3 imágenes.
- Tasa de finalización: % que genera/descarga PDF.
- Tiempo en página y uso de comparación antes/después.
- Reintentos: cuántos vuelven a generar otro informe para otra zona/fechas.

---

## Referencias internas

- Arquitectura y principios del sistema (costo cero, async-first, reproducibilidad, generación HD bajo demanda). :contentReference[oaicite:2]{index=2}
