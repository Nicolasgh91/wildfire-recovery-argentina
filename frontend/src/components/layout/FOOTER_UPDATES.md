I've implemented all the requested components and pages:

**Footer** (`/components/footer.tsx`): Redesigned with 4-column layout containing Product (Mapa de Incendios, Auditoría Legal, Reportes), Support (FAQ, Manual, Glosario), and Company (Contacto, API Docs external link) sections, plus copyright with branding message.

**Informational Pages:**

- `/app/faq/page.tsx`: Accordion-style FAQ with 5 realistic questions about wildfires, satellite data, FRP, NDVI, and Ley 26.815
- `/app/glossary/page.tsx`: Definition grid with 8 terms categorized as Satellite, Environmental, or Legal (FRP, NDVI, Ley 26.815, MODIS, VIIRS, etc.)
- `/app/manual/page.tsx`: Structured guide with sidebar navigation (desktop) and sheet drawer (mobile) covering Getting Started, Fire Map, Legal Audit, Reports, and Certificates


**Contact Page** (`/app/contact/page.tsx`): Full-featured form with auth integration that pre-fills and locks name/surname/email fields when logged in, subject dropdown (Support/Sales/Other), description textarea, optional file attachment with preview, loading state with spinner, and toast notifications for success/error.