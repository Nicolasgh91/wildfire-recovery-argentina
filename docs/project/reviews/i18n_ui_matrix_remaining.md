# Matriz final de i18n pendiente (UI)

| Ruta | Seccion UI | Texto actual (ES) | Clave propuesta | EN propuesto | Tipo | Prioridad |
|---|---|---|---|---|---|---|
| `frontend/src/pages/manual.tsx` | Header | Manual de Usuario | `manualTitle` | User Manual | label | alta |
| `frontend/src/pages/manual.tsx` | Header | Guia completa para utilizar ForestGuard | `manualSubtitle` | Complete guide to using ForestGuard | helper | alta |
| `frontend/src/pages/manual.tsx` | Navegacion | Navegacion / Contenido / Anterior / Siguiente | `manualNavigation` / `manualContent` / `manualPrevious` / `manualNext` | Navigation / Contents / Previous / Next | label | alta |
| `frontend/src/pages/manual.tsx` | Secciones y cuerpo | Primeros Pasos, Mapa de Incendios, Auditoria Legal, Reportes Ciudadanos, Certificados + parrafos/listas | `manualSection*`, `manualP*`, `manualLi*` | Section/title/body equivalents | long-copy | alta |
| `frontend/src/pages/faq.tsx` | Header | Preguntas Frecuentes | `faqTitle` | Frequently Asked Questions | label | alta |
| `frontend/src/pages/faq.tsx` | Header | Respuestas a las consultas mas comunes... | `faqSubtitle` | Answers to common wildfire monitoring questions | helper | alta |
| `frontend/src/pages/faq.tsx` | Accordion | Haz clic en cada pregunta para ver la respuesta | `faqHint` | Click each question to view the answer | helper | alta |
| `frontend/src/pages/faq.tsx` | Items | 5 preguntas + 5 respuestas hardcodeadas | `faqQ1..faqQ5`, `faqA1..faqA5` | English equivalents | long-copy | alta |
| `frontend/src/pages/faq.tsx` | CTA | No encontraste... / Contactanos directamente | `faqCtaPrompt`, `faqCtaAction` | Didn't find what you were looking for? / Contact us directly | label | media |
| `frontend/src/pages/glossary.tsx` | Header | Glosario / Terminos tecnicos... | `glossaryTitle`, `glossarySubtitle` | Glossary / Technical terms... | label | alta |
| `frontend/src/pages/glossary.tsx` | Categorias | Satelital / Ambiental / Legal | `glossaryCategorySatellite`, `glossaryCategoryEnvironmental`, `glossaryCategoryLegal` | Satellite / Environmental / Legal | label | alta |
| `frontend/src/pages/glossary.tsx` | Terminos | 8 definiciones hardcodeadas | `glossaryTerm*`, `glossaryDef*` | English equivalents | long-copy | alta |
| `frontend/src/pages/contact.tsx` | Header | Contacto / Tienes preguntas... | `contactPageTitle`, `contactPageSubtitle` | Contact / Have questions... | label | alta |
| `frontend/src/pages/contact.tsx` | Bloque alerta | Para consultas urgentes... | `contactPageUrgentMessage` | For urgent active-fire inquiries... | helper | alta |
| `frontend/src/components/contact/ContactForm.tsx` | Validaciones Zod | Nombre requerido, Correo invalido, etc. | `contactValidation*` | English equivalents | validation | alta |
| `frontend/src/components/contact/ContactForm.tsx` | Labels y placeholders | Nombre, Apellido, Correo..., Selecciona un asunto | `contactForm*` | English equivalents | label | alta |
| `frontend/src/components/contact/ContactForm.tsx` | Toasts | Consulta enviada con exito / Error al enviar consulta | `contactToastSuccessTitle`, `contactToastErrorTitle`, etc. | English equivalents | toast | alta |
| `frontend/src/components/contact/ContactForm.tsx` | Adjunto | Seleccionar archivo, Vista previa..., Formatos permitidos | `contactAttachment*` | English equivalents | helper | media |
| `frontend/src/components/layout/footer.tsx` | Columnas | Producto / Soporte / Informativos / Fuentes Publicas | `footerProduct`, `footerSupport`, `footerInformative`, `footerPublicSources` | Product / Support / Information / Public Sources | label | alta |
| `frontend/src/components/layout/footer.tsx` | Links internos | Historicos, Mapa de Incendios, etc. | `footerLink*` | English equivalents | label | alta |
| `frontend/src/components/layout/footer.tsx` | Brand copy | Plataforma de monitoreo... | `footerBrandLine1`, `footerBrandLine2` | English equivalents | helper | media |
| `frontend/src/components/layout/footer.tsx` | Dialog externo | Estas saliendo..., Vas a ser redirigido..., Cancelar/Continuar | `footerExternal*` | English equivalents | dialog | alta |
| `frontend/src/components/layout/footer.tsx` | Copyright | Todos los derechos reservados / Hecho con... | `footerCopyright`, `footerMadeWith`, `footerProtectForests` | English equivalents | helper | media |

## Nota de cobertura
- Esta matriz cubre el alcance restante confirmado en el barrido final.
- Se excluyen nombres propios, marcas y URLs (ForestGuard, CONAE, SNMF, etc.).
