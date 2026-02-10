# Justificación y objetivos de la mejora de UI/UX en la página de login/landing

## Contexto

ForestGuard busca acercar inteligencia satelital a personas no técnicas para que puedan **explorar evidencia visual** de lo que ocurrió en un terreno afectado por incendios en Argentina. La página de login/landing no es solo una “puerta de entrada”: es el primer contacto con la propuesta de valor y, por lo tanto, el lugar donde se define si el usuario entiende el propósito, confía en el producto y se anima a investigar.

Esta actualización de UI/UX se decidió para transformar una experiencia inicial potencialmente “técnica” o “fría” en una experiencia **más clara, accesible y orientada a la curiosidad**, sin perder credibilidad profesional.

---

## Problemas que se buscó resolver

1. **Barreras de comprensión en el primer impacto**
   - En interfaces con carga visual pesada o estilo excesivamente “cinemático”, el usuario no técnico puede interpretar el producto como complejo, técnico o inaccesible.
   - El mensaje central (investigar, comparar y entender) puede quedar oculto detrás del estilo.

2. **Fricción al iniciar sesión**
   - Si el formulario compite visualmente con el contenido o se percibe “duro”, el usuario siente esfuerzo antes de recibir valor.
   - Cualquier duda (qué hace la app, para qué sirve, por qué debería usarla) reduce la conversión.

3. **Falta de guía hacia el uso con fines de investigación**
   - Sin señales claras, el usuario puede no descubrir que la plataforma está pensada para “mirar el antes y el después”, aprender, comparar y tomar conciencia.

---

## Objetivos de la mejora

### Objetivo principal

**Aumentar la claridad, confianza y motivación del usuario no técnico** para que inicie sesión y explore evidencia satelital con una intención de investigación y concientización.

### Objetivos específicos

1. **Mejorar la comprensión inmediata del producto**
   - Que el usuario entienda en segundos: qué es ForestGuard, qué puede hacer y por qué es valioso.

2. **Reducir la fricción del acceso**
   - Hacer que el login se sienta simple, liviano y seguro.

3. **Incrementar la percepción de credibilidad**
   - Adoptar un lenguaje visual más “científico/profesional” para reforzar confianza en la evidencia presentada.

4. **Enfocar la experiencia en curiosidad guiada**
   - Orientar el “primer paso” del usuario a explorar, comparar y aprender (no solo “logearse y ya”).

5. **Mejorar legibilidad y jerarquía visual**
   - Priorizar lectura, estructura, y un recorrido visual claro: mensaje → valor → acción.

---

## Principios de diseño aplicados

1. **Claridad antes que espectacularidad**
   - Menos ruido visual, más mensaje y dirección.

2. **Confianza por diseño**
   - Un lenguaje visual sobrio y consistente reduce sospechas y aumenta la percepción de rigor.

3. **Jerarquía fuerte**
   - Un título dominante, un subtítulo explicativo y una leyenda que aterriza el “para qué”.

4. **Accesibilidad y legibilidad**
   - Contraste, espaciado, tipografía moderna y lectura cómoda.

5. **Curiosidad guiada**
   - Microcopy y estructura que invitan a explorar el antes/después y a interpretar cambios del terreno.

---

## Decisiones clave de UI/UX y su razón

### Fondo blanco como base (modo claro)

**Razón:** el fondo blanco cambia la percepción de “producto experimental” a “herramienta profesional”.  
**Impacto esperado:**
- Mejora la legibilidad.
- Reduce fatiga visual.
- Aumenta la sensación de precisión y seriedad (importante cuando se presenta evidencia satelital).

### Layout en dos columnas con imagen lateral

**Razón:** separar claramente “mensaje + acción” (texto y login) de “evidencia visual” (imagen).  
**Impacto esperado:**
- La imagen funciona como “ventana al territorio” y dispara curiosidad.
- El formulario no compite con la narrativa; acompaña.

### Animación premium del título (revelado tipo “tinta”)

**Razón:** convertir el título en un momento de atención sin convertir la página en un show.  
**Impacto esperado:**
- Refuerza sensación tecnológica.
- Crea una primera impresión memorable, sin sacrificar claridad.
- Sugiere “descubrimiento” (el texto se revela como evidencia que aparece).

### Formulario minimalista y liviano

**Razón:** el login debe ser un paso rápido, no un obstáculo.  
**Impacto esperado:**
- Menos “peso visual” = menos sensación de complejidad.
- Mayor foco en el propósito del producto.
- Mejor percepción de modernidad y cuidado.

---

## Cómo la nueva interfaz atrae uso para investigación, curiosidad y concientización

### Investigación (explorar evidencia)

- El copy enfatiza **líneas de tiempo satelitales** y comparación **antes/después**.
- La imagen lateral sugiere “esto es sobre el terreno real”, no sobre métricas abstractas.

### Curiosidad (invitar a mirar mejor)

- La narrativa “vista desde el espacio” funciona como gancho: despierta preguntas naturales:
  - “¿Qué cambió en ese lugar?”
  - “¿Se recuperó?”
  - “¿Hay nuevas construcciones?”
- La jerarquía del texto está diseñada para empujar a explorar, no solo a entrar.

### Concientización (entender el impacto)

- La propuesta se centra en observar consecuencias y evolución del territorio.
- La estética sobria evita sensacionalismo y refuerza el foco en evidencia y aprendizaje.

---

## Métricas sugeridas para evaluar si la mejora cumplió su objetivo

1. **Tasa de conversión de landing → login exitoso**
2. **Tiempo hasta la primera acción significativa**
   - Ej.: abrir historial, seleccionar un área, iniciar una comparación temporal.
3. **Tasa de rebote en la landing**
4. **Interacciones con elementos guía**
   - Ej.: clicks en “verificar”, “explorar”, “comparar antes y después”.
5. **Feedback cualitativo**
   - Pregunta simple post-uso: “¿Te resultó claro qué podés hacer con ForestGuard?”

---

## Riesgos considerados y mitigaciones

- **Riesgo:** que el estilo “demasiado limpio” se perciba como genérico.  
  **Mitigación:** mantener un elemento distintivo (animación del H1 + imagen “ventana al terreno” + copy con identidad).

- **Riesgo:** que la animación distraiga o afecte performance.  
  **Mitigación:** animación sutil, duración corta, preferencia por `prefers-reduced-motion` para accesibilidad.

- **Riesgo:** que el usuario no entienda qué obtiene tras loguearse.  
  **Mitigación:** reforzar la propuesta de valor con subtítulo y leyenda orientada a casos concretos (revegetación, construcciones no autorizadas).

---

## Conclusión

La mejora de UI/UX en la página de login/landing se decidió para **aumentar claridad, confianza y motivación**, con una estética más profesional y una narrativa diseñada para activar el modo mental correcto: *“voy a explorar evidencia y entender qué pasó en un lugar”*. El resultado esperado es una experiencia más amigable para el público no técnico, que incentiva el uso con fines de investigación, curiosidad y concientización, alineada con el propósito central de ForestGuard.
