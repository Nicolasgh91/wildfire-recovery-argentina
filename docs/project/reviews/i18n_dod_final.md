# DoD Final - Auditoria i18n UI (cobertura total del alcance)

## Alcance cerrado en esta iteracion
- `frontend/src/pages/manual.tsx`
- `frontend/src/pages/faq.tsx`
- `frontend/src/pages/glossary.tsx`
- `frontend/src/pages/contact.tsx`
- `frontend/src/components/contact/ContactForm.tsx`
- `frontend/src/components/layout/footer.tsx`
- `frontend/src/data/translations.ts`

## Checklist DoD

### 1. Cobertura i18n
- [x] Textos UI del alcance restante migrados a `t()`.
- [x] Claves ES/EN agregadas en `translations.ts` para manual/faq/glossary/contact/footer.
- [x] No quedan literales UI hardcodeados en los 6 archivos objetivo (excepto marca/URLs y nombres propios externos).

### 2. Consistencia tecnica
- [x] Componentes consumen `useI18n()`.
- [x] Validaciones y toasts de `ContactForm` usan claves i18n.
- [x] Footer (labels, tooltips, dialogo externo, copyright) usa claves i18n.

### 3. Regresion
- [x] Tests nuevos agregados:
  - `src/__tests__/manual-page.i18n.test.tsx`
  - `src/__tests__/contact-form.i18n.test.tsx`
  - `src/__tests__/footer.i18n.test.tsx`
- [x] Tests base de i18n existentes se mantienen pasando.

### 4. Verificacion ejecutada
Comando:

```bash
npm run test:run -- src/__tests__/manual-page.i18n.test.tsx src/__tests__/contact-form.i18n.test.tsx src/__tests__/footer.i18n.test.tsx src/__tests__/language-context.test.tsx src/__tests__/not-found.test.tsx src/__tests__/fire-card.test.tsx
```

Resultado:
- `Test Files: 6 passed`
- `Tests: 20 passed`

### 5. Riesgos residuales
- **Long-copy en translations.ts**: crecio significativamente; recomendable segmentar por dominio (manual/faq/glossary/contact/footer) en una siguiente iteracion para mantenibilidad.
- **Editor TS vs runner**: el IDE muestra errores de resolucion de alias en algunos tests, pero Vitest ejecuta en verde. Riesgo bajo, conviene alinear configuracion de TS server del editor.
- **Textos regulatorios externos**: enlaces/fuentes publicas cambian con el tiempo; revisar periodicamente labels/tooltips.

## Evidencia complementaria
- Matriz de pendiente y trazabilidad de claves:
  - `review/i18n_ui_matrix_remaining.md`
