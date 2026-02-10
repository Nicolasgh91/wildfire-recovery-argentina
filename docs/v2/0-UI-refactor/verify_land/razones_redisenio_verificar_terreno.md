# Razones y objetivos del rediseño UX/UI en la página “Verificar terreno”

Fecha: 2026-02-09

## Resumen ejecutivo

Se decidió aplicar una mejora de UX/UI en la página anteriormente denominada “Auditoría” para transformarla en “Verificar terreno” con un propósito claro: **hacer que una persona no técnica pueda investigar por su cuenta el historial de incendios y la evolución del terreno**, interpretando evidencia de forma guiada y comprensible.

El rediseño no solo busca “verse mejor”. Su objetivo principal es **aumentar la adopción, reducir fricción y generar confianza**, promoviendo un uso orientado a **investigación, curiosidad y concientización** sobre incendios forestales y sus efectos en el paisaje.

---

## Contexto del problema

La interfaz previa estaba diseñada con un enfoque técnico:
- Priorizaba coordenadas, radio en metros e identificadores.
- Utilizaba terminología administrativa (“auditoría”, “ejecutar auditoría”).
- Presentaba un flujo centrado en datos, no en la intención del usuario final.
- Dejaba gran parte de la pantalla sin contenido significativo antes de ejecutar una acción.

Esto generaba barreras para el público general:
- Requería conocimientos que el usuario promedio no tiene (latitud/longitud).
- Transmitía una sensación de trámite o proceso legal.
- No explicaba claramente qué se obtendría como resultado.
- No reforzaba un “por qué” relevante para la persona: aprender, verificar, comparar, entender.

---

## Objetivos del cambio

### 1) Reducir fricción para usuarios no técnicos
La nueva interfaz está diseñada para que el usuario pueda completar el flujo **sin entender coordenadas**. Se prioriza un lenguaje y controles que representen el mundo real:
- Buscar por dirección, localidad, parque nacional o provincia.
- Marcar un punto en el mapa como acción principal.
- Seleccionar un “área de análisis” con opciones entendibles.

### 2) Aumentar comprensión y percepción de valor
Se incorporan elementos que explican “qué voy a obtener” antes de pedir una acción:
- Estado vacío con “lo que vas a ver”.
- Resultados estructurados y progresivos.
- Checklist de verificación para guiar la lectura.

Esto incrementa:
- Claridad del propósito.
- Confianza del usuario.
- Persistencia en la tarea (menos abandono).

### 3) Cambiar el posicionamiento: de trámite a investigación ciudadana
Se reemplaza el concepto de “auditoría” por “verificación” para:
- Evitar connotaciones legales o burocráticas.
- Enfatizar exploración y aprendizaje.
- Invitar a mirar evidencia y formular conclusiones personales.

### 4) Promover curiosidad guiada y concientización
La nueva UI integra microcopy estratégico que:
- Incentiva a observar evidencia.
- Evita afirmaciones absolutas o sesgos.
- Enmarca el análisis como una herramienta de contraste y aprendizaje.

Ejemplos del enfoque:
- “Acá podés mirar evidencia y sacar tus conclusiones.”
- “Esto no demuestra intencionalidad por sí solo. Sirve para contrastar relatos con evidencia observable.”

### 5) Ordenar el flujo mental del usuario
La interfaz se reestructura para que el recorrido sea natural:

**Antes:** datos → ejecutar → resultados  
**Ahora:** lugar → mapa → verificación → evidencia/interpretación

Este cambio alinea el producto con la forma real en que los usuarios piensan y actúan.

---

## Principios de diseño aplicados

### Lenguaje centrado en el usuario
- Se sustituyen términos técnicos por acciones simples y directas.
- El CTA “Verificá” es una invitación clara, corta y entendible.

### Jerarquía visual y foco en el mapa
- El mapa pasa a ser el protagonista “above the fold”.
- Los campos técnicos se mueven a “Opciones avanzadas”.

### Accesibilidad cognitiva
Se reduce la carga mental con:
- Opciones predefinidas de área (500 m, 1 km, 3 km).
- Estados guiados (vacío, cargando, error) con mensajes accionables.
- Checklist para orientar la lectura de resultados.

### Evidencia primero, conclusiones después
La UI refuerza un orden responsable:
1. Ver datos y evidencia visual.
2. Interpretar con guía.
3. Formar conclusiones personales sin forzar una narrativa.

---

## Cómo la nueva interfaz atrae uso para investigación, curiosidad y concientización

### Investigación
- Estructura de resultados clara y repetible para comparar zonas.
- Checklist para evaluar preguntas clave.
- Evidencia visual organizada (thumbnails con fechas y metadatos).

### Curiosidad
- Microcopy que invita a explorar sin juzgar.
- Flujo simple que facilita “probar” distintas ubicaciones rápidamente.
- Menos fricción inicial: el usuario empieza por un lugar conocido.

### Concientización
- Pone en primer plano efectos visibles: cicatrices, recuperación, degradación.
- Favorece comprensión del impacto ambiental en el tiempo.
- Ayuda a distinguir entre afirmaciones en redes y lo observable.

---

## Resultados esperados

### Métricas de producto (esperables)
- Mayor tasa de inicio de flujo (más usuarios presionan “Verificá”).
- Menor tasa de abandono (la interfaz explica y guía mejor).
- Mayor tiempo en página y exploración de evidencia.
- Mayor intención de registro para acceder a descargas (si aplica gating).

### Resultados cualitativos
- El usuario siente que la herramienta “es para mí”.
- La experiencia se percibe confiable y educativa.
- Se refuerza el rol del usuario como investigador activo.

---

## Conclusión

La mejora de UX/UI se implementó para **alinear la página con su propósito real**: habilitar a la ciudadanía a verificar incendios históricos y comprender la evolución del territorio de forma accesible.

Al priorizar mapa, lenguaje simple, estados informativos y guía de interpretación, la interfaz se vuelve más amigable y efectiva, fomentando un uso orientado a **investigación, curiosidad y concientización**.
