# Objetivo y alcance
Fecha de corte del relevamiento: 2026-02-26.

Este documento define un reporte inicial completo para actualizar y extender la FAQ publica de la app. El foco es ayudar a personas no tecnicas a entender que puede hacer hoy la plataforma, con lenguaje simple y accionable.

Alcance de este entregable:
- Auditar la FAQ actual de `/faq` (11 preguntas/respuestas).
- Verificar cobertura contra funcionalidades reales del producto.
- Proponer un banco extendido de 25-30 FAQ nuevas en espanol simple.
- Evitar terminologia de reportes, auditoria y legales dentro de las nuevas preguntas y respuestas.
- Dejar lineamientos concretos para una futura implementacion en UI/i18n (sin ejecutar cambios de codigo en este turno).

Fuentes revisadas para este relevamiento:
- `frontend/src/pages/faq.tsx`
- `frontend/src/data/translations.ts`
- `frontend/src/App.tsx`
- `docs/product/estado-real-del-producto.md`
- `docs/product/casos-de-uso-y-estado.md`
- `docs/frontend/README.md`
- `frontend/src/config/brand.ts`

Contexto de public interfaces en esta fase:
- No hay cambios en API/backend.
- No hay cambios en tipos/rutas frontend.
- Se agrega solo documentacion en `docs/faqs`.

# Estado actual de FAQ (/faq)
Estado verificado de la pagina actual:
- La vista `frontend/src/pages/faq.tsx` renderiza un acordeon con 11 items fijos (`faqQ1..faqQ11` y `faqA1..faqA11`).
- El contenido real esta en `frontend/src/data/translations.ts` (ES/EN).
- La pagina es publica (`/faq`) segun `frontend/src/App.tsx`.

Resumen de contenido actual:
- 11 preguntas orientadas mayormente a fuentes satelitales y conceptos tecnicos.
- Enfoque fuerte en FRP, NDVI, MODIS/VIIRS, GEE y marco normativo.
- Cobertura baja de flujos de uso recientes (exploracion guiada, cuenta, creditos/pagos, contacto, funciones con feature flag).

# Hallazgos de revisión (contenido actual)
## Hallazgos principales
1. Exceso de tecnicismos para usuario general.
- Se usan explicaciones extensas de FRP/NDVI/MODIS/VIIRS y detalle de infraestructura.
- Falta orientacion directa a "que puedo hacer ahora en la app".

2. Sesgo de narrativa no alineado con estado actual del producto.
- El tono actual de FAQ conserva foco historico en marco legal/auditoria.
- La narrativa canon vigente del producto prioriza exploracion guiada y evidencia visual simple.

3. Cobertura incompleta de funcionalidades nuevas o ampliadas.
- No cubre bien exploracion guiada de 3 pasos.
- No cubre en forma clara creditos y retorno de pago.
- No cubre perfil/cuenta y seguridad de acceso.
- No cubre contacto con adjuntos y validaciones.
- No cubre disponibilidad parcial por feature flags.

4. Desalineaciones de exactitud detectadas.
- Umbrales de severidad:
  - FAQ actual menciona bandas de FRP (<100, 100-500, >500, >1000).
  - UI usa umbrales de severidad mas bajos (20/50) en `frontend/src/types/fire.ts` y `frontend/src/pages/MapPage.tsx`.
- Frecuencia/tiempo real:
  - FAQ actual habla de "6-12 horas" y de ingesta "cada 12 horas".
  - Scheduling operativo actual muestra corrida diaria de ingesta (`workers/celery_app.py`, tarea `download-firms-daily` 00:00 ART).
- Aviso ciudadano:
  - FAQ actual lo presenta como flujo totalmente operativo de punta a punta.
  - En frontend, `frontend/src/pages/CitizenReport.tsx` usa simulacion local (`setTimeout`) y no envio final real.
- Certificados:
  - FAQ actual puede leerse como flujo plenamente disponible.
  - En frontend, `frontend/src/pages/Certificates.tsx` usa mock local.
  - En backend, certificados requieren feature + API key (`app/main.py`, `app/api/routes/certificates.py`).

5. Inconsistencia de naming de marca.
- Gran parte del copy aun menciona "ForestGuard" en traducciones.
- Configuracion de marca actual en frontend define `Vestigia` (`frontend/src/config/brand.ts`).

## Implicancia para la nueva FAQ
- La nueva FAQ debe pasar de "explicar tecnologia" a "guiar decisiones y acciones del usuario".
- Debe declarar de forma simple cuando algo esta en modo parcial o depende de configuracion.
- Debe usar naming de marca unificado para evitar confusion.

# Cobertura funcional vs FAQ actual
| Funcionalidad | Ruta | Estado actual | FAQ actual la cubre? | Nueva FAQ propuesta? |
|---|---|---|---|---|
| Inicio | `/home` | Publicada | No | Si (FAQ 1, 6, 9) |
| Mapa | `/map` | Publicada | Parcial | Si (FAQ 10, 11, 17) |
| Historico | `/fires/history` | Publicada (auth) | Parcial | Si (FAQ 12, 13) |
| Detalle de incendio | `/fires/:id` | Publicada (con ajustes UX) | No | Si (FAQ 14, 15) |
| Exploracion guiada | `/exploracion` | Publicada | No | Si (FAQ 16, 18, 19, 20) |
| Creditos | `/credits` | Parcial estable | No | Si (FAQ 23, 24, 25) |
| Retorno de pago | `/payments/return` | Parcial estable | No | Si (FAQ 26) |
| Login/Registro/Perfil | `/login`, `/register`, `/profile` | Publicada | No | Si (FAQ 2, 3, 4, 21, 22) |
| Contacto | `/contact` | Publicada | No | Si (FAQ 29, 30) |
| Aviso ciudadano | `/citizen-report` | Parcial (envio final en ajuste) | Parcial | Si (FAQ 27) |
| Certificados | `/certificates` | Parcial (flag + mock frontend) | Parcial | Si (FAQ 28) |
| Refugios | `/shelters` | Parcial (flag) | No | Si (FAQ 28) |
| Manual/Glosario/FAQ | `/manual`, `/glossary`, `/faq` | Publicada | Parcial | Si (FAQ 5, 30) |

# Criterios editoriales para nueva FAQ (no técnica)
Reglas editoriales para redactar la nueva FAQ:
1. Lenguaje simple y directo, orientado a "que puedo hacer".
2. Primero valor practico, despues detalle.
3. Respuestas cortas: 2 a 4 frases.
4. Incluir pasos concretos cuando corresponda.
5. Mostrar limites reales sin tono tecnico denso.
6. Si una funcion no esta disponible para todos: usar formula "disponible segun configuracion".
7. Unificar naming de marca en toda la FAQ (usar Vestigia).
8. Evitar en nuevas preguntas/respuestas estas palabras: `reporte`, `auditoria`, `legal`.

Checklist de tono esperado en cada FAQ:
- Entendible por alguien que entra por primera vez.
- Sin siglas tecnicas no explicadas.
- Con accion sugerida ("entra a...", "elegi...", "proba...").

# Propuesta extendida de FAQs (banco inicial completo)
Banco inicial propuesto: 30 FAQ nuevas.

## Empezar a usar la plataforma
| # | Pregunta | Respuesta (version simple) | Funcionalidad cubierta | Estado |
|---|---|---|---|---|
| 1 | Que puedo hacer en Vestigia si entro por primera vez? | Podes ver incendios recientes y pasados, navegar el mapa y explorar zonas en pocos pasos. Si queres guardar avances y usar funciones completas, te conviene iniciar sesion. Empeza por Inicio y despues entra a Exploracion. | `/home`, `/exploracion` | Publicada |
| 2 | Necesito cuenta para usar la app? | No para mirar contenido publico. Si queres guardar tu trabajo, usar tu perfil y avanzar en funciones personales, si necesitas cuenta. Podes crearla en menos de un minuto. | `/home`, `/login`, `/register` | Publicada |
| 3 | Como creo mi cuenta? | Entra a Registrarse, completa tus datos y segui el paso de confirmacion. Cuando termines, volve a iniciar sesion y ya vas a tener acceso a tu espacio personal. | `/register` | Publicada |
| 4 | Puedo entrar sin contraseña? | Si, hay opcion de acceso por enlace al correo. Tambien podes usar acceso con cuenta externa segun disponibilidad. Elegi la opcion que te resulte mas comoda en Login. | `/login`, `/auth/callback` | Publicada |
| 5 | Donde encuentro ayuda para aprender a usar cada seccion? | Tenes tres apoyos: FAQ para dudas rapidas, Manual para guias paso a paso y Glosario para terminos puntuales. Si aun asi te trabas, podes escribirnos desde Contacto. | `/faq`, `/manual`, `/glossary`, `/contact` | Publicada |

## Ver incendios y buscar zonas
| # | Pregunta | Respuesta (version simple) | Funcionalidad cubierta | Estado |
|---|---|---|---|---|
| 6 | Que diferencia hay entre Inicio y Mapa? | Inicio te muestra tarjetas para recorrer casos rapido. Mapa te deja ubicar visualmente cada caso y moverte por zona. Si queres orientarte primero, empeza por Inicio; si queres ubicarte exacto, usa Mapa. | `/home`, `/map` | Publicada |
| 7 | Que significa "activo" y "reciente"? | Activo indica actividad actual o muy cercana en el tiempo. Reciente muestra casos cerrados o en transicion dentro de una ventana cercana. Asi podes entender que esta pasando ahora y que paso hace poco. | `/home`, `/map` | Publicada |
| 8 | Como busco una provincia en segundos? | Usa los filtros de la parte superior y elegi la provincia. Si queres afinar mas, combina provincia con fechas o texto. Si no aparece nada, cambia rango de fecha y volve a intentar. | `/home`, `/fires/history` | Publicada |
| 9 | No veo casos en mi zona, es normal? | Si, puede pasar segun fecha, zona o filtros activos. Primero limpia filtros y revisa un rango mas amplio. Tambien podes cambiar entre Inicio, Mapa e Historico para ampliar resultados. | `/home`, `/map`, `/fires/history` | Publicada |
| 10 | Como abro el detalle de un incendio? | Desde una tarjeta o desde el mapa, toca "Ver detalles". En esa vista vas a ver ubicacion, fechas, area y otros datos utiles en un solo lugar. Es el mejor punto para revisar un caso puntual. | `/home`, `/map`, `/fires/:id` | Publicada |
| 11 | Por que en Mapa veo casos que no vi en Inicio? | Cada pantalla prioriza una forma distinta de mostrar informacion. Inicio esta pensado para lectura rapida y Mapa para lectura geografica. Si queres cobertura maxima, usa ambas vistas en conjunto. | `/home`, `/map` | Publicada |
| 12 | Para que sirve Historico? | Historico sirve para analizar volumen, tendencias y comparaciones por periodo. Podes aplicar filtros, ordenar resultados y recorrer una tabla mas completa. Es ideal cuando queres una vista mas amplia en el tiempo. | `/fires/history` | Publicada |
| 13 | Puedo bajar los datos de Historico? | Si, tenes opcion de exportacion en CSV. Antes de bajar, defini bien filtros y fechas para que el archivo salga con lo que realmente necesitas. | `/fires/history` | Publicada |
| 14 | Que datos voy a encontrar en el detalle de un caso? | Vas a encontrar fecha, provincia, area estimada, coordenadas y estado general. Segun el caso tambien vas a ver paneles de evolucion y datos adicionales. Si faltan campos, suele ser porque ese dato aun no esta disponible para ese caso puntual. | `/fires/:id` | Publicada |
| 15 | Que significa "calidad de datos" en un caso? | Es una forma simple de mostrar cuan completa y consistente esta la informacion visible. Te ayuda a interpretar mejor lo que estas viendo. Si ves valores vacios, no siempre es error: a veces es falta de dato de origen. | `/fires/:id` | Publicada |

## Comparar antes/despues de un incendio
| # | Pregunta | Respuesta (version simple) | Funcionalidad cubierta | Estado |
|---|---|---|---|---|
| 16 | Como funciona Exploracion paso a paso? | Es un flujo guiado de 3 pasos: elegir caso, elegir fechas y confirmar generacion. En cada paso ves claramente que falta para avanzar. Si seguis ese orden, el proceso es rapido y claro. | `/exploracion` | Publicada |
| 17 | Puedo elegir un incendio desde el mapa dentro de Exploracion? | Si. En el paso inicial podes abrir el mapa, tocar un punto y seleccionar el caso. Es util cuando sabes la zona pero no el nombre exacto. | `/exploracion` | Publicada |
| 18 | Cuantas fechas puedo usar para comparar? | Podes usar hasta 12 fechas en total. La app te propone combinaciones rapidas y tambien te deja ajustar manualmente. Si queres detalle temporal fino, suma mas fechas de forma gradual. | `/exploracion` | Publicada |
| 19 | Puedo guardar mi trabajo y seguir despues? | Si, podes guardar tu avance para retomarlo luego. Te conviene poner un titulo claro para encontrarlo facil. | `/exploracion` | Publicada |
| 20 | Que puedo detectar al comparar antes y despues? | Podes observar cambios de cobertura vegetal, movimiento de suelo, aperturas y otras variaciones visibles. La idea es ayudarte a mirar el cambio en el tiempo con material visual comparable. | `/exploracion` | Publicada |

## Imagenes y por que a veces no aparecen como espero
| # | Pregunta | Respuesta (version simple) | Funcionalidad cubierta | Estado |
|---|---|---|---|---|
| 21 | Por que algunas imagenes tardan en aparecer? | Porque se generan a pedido y pueden quedar en cola cuando hay mucha demanda. Espera unos minutos y refresca el estado. Si sigue igual, volve a intentar con menos fechas. | `/exploracion`, `/fires/:id` | Publicada |
| 22 | Por que una imagen se ve con nubes o poco clara? | La captura depende de las condiciones del dia en esa zona. Proba con otras fechas cercanas para mejorar visibilidad. Cuantas mas fechas pruebes, mas chances de encontrar una vista util. | `/exploracion`, `/fires/:id` | Publicada |

## Cuenta, acceso y seguridad basica
| # | Pregunta | Respuesta (version simple) | Funcionalidad cubierta | Estado |
|---|---|---|---|---|
| 23 | Donde cambio mis datos de cuenta? | En Perfil podes editar tu nombre y revisar tu saldo. Desde ahi tambien tenes acciones de seguridad de cuenta. | `/profile` | Publicada |
| 24 | La sesion se cierra sola si no uso la app? | Si, por seguridad hay cierre automatico por inactividad. Si pasa, volve a iniciar sesion y continua donde estabas. | `/login`, `/profile` | Publicada |
| 25 | Que pasa si no puedo completar el inicio con cuenta externa? | La app muestra un estado de espera y opciones para reintentar. Si no avanza, volve a Login y probalo otra vez. | `/auth/callback`, `/login` | Publicada |

## Creditos y pagos
| # | Pregunta | Respuesta (version simple) | Funcionalidad cubierta | Estado |
|---|---|---|---|---|
| 26 | Para que sirven los creditos? | Sirven para ejecutar funciones de generacion bajo demanda. Antes de confirmar, la app te muestra el costo estimado para que decidas con claridad. | `/credits`, `/exploracion` | Parcial estable |
| 27 | Como cargo creditos? | Entra a Creditos, elegi la cantidad y segui el checkout. Cuando el pago se confirma, el saldo se actualiza en tu cuenta. | `/credits`, `/payments/return` | Parcial estable |
| 28 | Mi pago quedo "en proceso", que hago? | Espera unos minutos y revisa la pantalla de retorno de pago. Si todavia no cambia, entra de nuevo desde Creditos. El estado puede demorar segun el medio de pago. | `/payments/return`, `/credits` | Parcial estable |

## Funciones adicionales (con aclaracion de disponibilidad)
| # | Pregunta | Respuesta (version simple) | Funcionalidad cubierta | Estado |
|---|---|---|---|---|
| 29 | Puedo dejar un aviso ciudadano desde la app? | Si, tenes un asistente para cargar ubicacion, imagen y descripcion. Hoy esa experiencia esta disponible y en mejora de cierre final de envio, segun entorno activo. | `/citizen-report` | Parcial |
| 30 | Veo Certificados o Refugios en todos los entornos? | No siempre. Son funciones disponibles segun configuracion de cada entorno. Si no las ves, no es un error de tu cuenta: puede estar desactivado en esa instancia. | `/certificates`, `/shelters` | Por flag |

# Priorización para publicar (MVP FAQ)
Criterio aplicado:
- Mayor frecuencia de duda esperada en primer uso.
- Menor complejidad de lectura.
- Menor riesgo de confusion operativa.

Top 12 FAQ para publicar primero:
1. FAQ 1 - Que puedo hacer en Vestigia si entro por primera vez?
2. FAQ 2 - Necesito cuenta para usar la app?
3. FAQ 6 - Que diferencia hay entre Inicio y Mapa?
4. FAQ 8 - Como busco una provincia en segundos?
5. FAQ 10 - Como abro el detalle de un incendio?
6. FAQ 12 - Para que sirve Historico?
7. FAQ 16 - Como funciona Exploracion paso a paso?
8. FAQ 18 - Cuantas fechas puedo usar para comparar?
9. FAQ 21 - Por que algunas imagenes tardan en aparecer?
10. FAQ 26 - Para que sirven los creditos?
11. FAQ 27 - Como cargo creditos?
12. FAQ 29 - Puedo dejar un aviso ciudadano desde la app?

Segunda tanda sugerida:
- FAQ 3, 4, 5, 7, 9, 11, 13, 14, 15, 17, 19, 20, 22, 23, 24, 25, 28, 30.

# Riesgos de comunicación y mitigaciones
| Riesgo | Impacto | Mitigacion propuesta |
|---|---|---|
| Mantener tecnicismos en exceso | Baja comprension en usuario no tecnico | Aplicar checklist editorial y revision de claridad antes de publicar |
| No aclarar funciones parciales o por flag | Frustracion por expectativas incorrectas | Incluir nota estandar: "disponible segun configuracion" |
| Desfase entre FAQ y estado real de producto | Perdida de confianza | Revalidar FAQ contra rutas/flags cada ciclo de release |
| Mezcla de naming (ForestGuard/Vestigia) | Confusion de marca | Unificar marca visible en FAQ y microcopy de ayuda |
| Explicaciones largas sin accion | Baja utilidad practica | Forzar formato corto (2-4 frases) con un "que hacer" concreto |

# Próximos pasos de implementación (fuera de este reporte)
Checklist de ejecucion posterior:
- [ ] Actualizar claves i18n de FAQ en `frontend/src/data/translations.ts` (nuevo set FAQ ES/EN).
- [ ] Ajustar lista de items en `frontend/src/pages/faq.tsx` para la nueva cantidad.
- [ ] Ajustar subtitulo y hint de FAQ al tono no tecnico.
- [ ] Revisar consistencia de marca en FAQ (Vestigia).
- [ ] Validar version EN en segunda iteracion editorial.
- [ ] QA funcional de copy vs rutas activas y feature flags.

## Casos de prueba/validacion del reporte
1. Cobertura: toda ruta funcional principal debe figurar en la matriz.
2. Tono: ninguna FAQ nueva debe usar terminologia de reportes/auditoria/legal.
3. Claridad: cada respuesta debe entenderse sin conocimiento tecnico.
4. Exactitud: cada FAQ nueva debe mapear a estado real (publicada/parcial/por flag).
5. Consistencia de marca: naming final unificado en Vestigia.
6. Accionabilidad: al menos 70% de respuestas con paso concreto de uso.

## Supuestos y decisiones tomadas
- Profundidad elegida: Completo.
- Cobertura elegida: incluye funcionalidades parciales con aclaracion.
- Idioma del reporte: espanol.
- Este entregable es documental; no modifica frontend/backend.
- Se prioriza comprension de usuario no tecnico por sobre detalle interno.
