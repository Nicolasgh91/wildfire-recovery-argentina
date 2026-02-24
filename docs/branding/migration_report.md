# Branding Migration Report: UI Inventory For Final Rename

## 1. Cobertura y criterio

### Alcance
- Solo UI renderizada.
- Se incluyen términos de marca y dominio funcional en UI: `ForestGuard`, `Vestigia`, `Wildfire/wildfires`.
- Se considera que `Wildfire/wildfires` debe quedar centralizado para el rename final.

### Fuentes verificadas
- `frontend/src/App.tsx` (rutas y shell layout).
- `frontend/src/lib/routing.ts` (`HOME_PATH = /home`).
- `frontend/src/data/translations.ts` (ES/EN).
- `frontend/index.html` (title/meta SEO).
- `frontend/src/components/layout/navbar.tsx`.
- `frontend/src/components/layout/footer.tsx`.
- `frontend/src/features/navigation/components/navigation-drawer.tsx`.
- `frontend/src/features/navigation/components/navigation-topbar-tablet.tsx`.
- `frontend/src/features/navigation/components/external-confirm-dialog.tsx`.
- `frontend/src/features/navigation/config/navigation.ts`.
- `frontend/src/features/navigation/config/public-sources.ts`.
- `frontend/src/pages/*` (mapeo page-by-page).
- `frontend/src/config/brand.ts` (fuente central actual).

### Reglas de clasificación
- `texto_plano`: literal hardcodeado o texto i18n no parametrizado por `brand.ts`.
- `variable`: valor inyectado desde `BRAND`.
- `centralizado en brand.ts = si`: depende de `BRAND` hoy.
- `centralizado en brand.ts = no`: no depende de `BRAND` hoy.
- `centralizado en brand.ts = parcial`: mezcla de contenido centralizado y no centralizado en la misma superficie.

### Exclusiones explícitas
- No se incluye inventario principal de claves no renderizadas actualmente:
  - `loginWelcome`.
  - `footerExternalDailyReportTooltip`.
- No se incluyen strings técnicos no visibles en UI (ejemplo: storage keys, comments, package name).

## 2. Inventario global (shell UI)

| Superficie | Archivo | Clave/Literal | Tipo (texto_plano\|variable) | Centralizado en brand.ts (si/no) | Observación |
| --- | --- | --- | --- | --- | --- |
| Label de marca principal (navbar/footer/drawer/topbar/login/register) | `frontend/src/components/layout/navbar.tsx`;<br>`frontend/src/components/layout/footer.tsx`;<br>`frontend/src/features/navigation/components/navigation-drawer.tsx`;<br>`frontend/src/features/navigation/components/navigation-topbar-tablet.tsx`;<br>`frontend/src/pages/Login.tsx`;<br>`frontend/src/pages/Register.tsx` | `BRAND.name` | variable | si | Valor actual: `Vestigia`. En `App.tsx`, el shell global no se renderiza en `/`, `/login`, `/register`. |
| SEO title HTML | `frontend/index.html` | `<title>Vestigia | Monitoreo de incendios forestales</title>` | texto_plano | no | Debe pasar a `BRAND.seo.title`. |
| SEO meta description HTML | `frontend/index.html` | `Argentina wildfire recovery and monitoring platform...` | texto_plano | no | Contiene `wildfire/wildfires`; debe pasar a `BRAND.seo.description`. |
| Link externo API docs | `frontend/src/features/navigation/config/navigation.ts` | `https://forestguard.freedynamicdns.org/docs` | texto_plano | no | URL hardcodeada; debe pasar a `BRAND.links.docsUrl`. |
| Claim en footer (EN) | `frontend/src/data/translations.ts` (key `footerBrandLine1`), consumida en `frontend/src/components/layout/footer.tsx` | `Monitoring and recovery platform for wildfires in Argentina.` | texto_plano | no | Debe parametrizar `wildfires` con `{wildfireTerm}`. |
| Título de salida a externos | `frontend/src/data/translations.ts` (key `footerLeavingTitle`), consumida en `frontend/src/features/navigation/components/external-confirm-dialog.tsx` | `You are leaving ForestGuard` / `Estás saliendo de ForestGuard` | texto_plano | no | Debe parametrizar `ForestGuard` con `{brandName}`. |
| Label reporte diario (EN) | `frontend/src/data/translations.ts` (key `footerExternalDailyReportLabel`), consumida vía `frontend/src/features/navigation/config/navigation.ts` | `Daily wildfire report` | texto_plano | no | Debe parametrizar `wildfire` con `{wildfireTerm}`. |
| Tooltip SNMF (EN) | `frontend/src/data/translations.ts` (key `footerExternalSnmfTooltip`), consumida vía `frontend/src/features/navigation/config/public-sources.ts` | `Official SNMF site with wildfire information in Argentina.` | texto_plano | no | Debe parametrizar `wildfire` con `{wildfireTerm}`. |

## 3. Inventario por ruta (page-by-page)

| Ruta | Componente | Ocurrencias | Tipo | Centralizado en brand.ts | Acción |
| --- | --- | --- | --- | --- | --- |
| `/` | `RootRouteGate` | Sin UI de marca; ruta de redirección por estado de auth. | n/a | n/a | Sin acción (redirección). |
| `/home` (`HOME_PATH`) | `HomePage` | `fireFeed` (EN: `Wildfire Feed`) + shell global. | texto_plano (i18n) + variable (shell) | parcial | Parametrizar `fireFeed` con `{wildfireTerm}`. |
| `/map` | `MapPage` | Sin ocurrencias locales; usa shell global. | variable (shell) | si (solo shell) | Sin acción local. |
| `/audit` | `AuditPage` | Sin ocurrencias locales; usa shell global. | variable (shell) | si (solo shell) | Sin acción local. |
| `/credits` | `CreditsPage` | Sin ocurrencias locales; usa shell global. | variable (shell) | si (solo shell) | Sin acción local. |
| `/exploracion` | `ExplorationPage` | Sin ocurrencias locales; usa shell global. | variable (shell) | si (solo shell) | Sin acción local. |
| `/reports` | `Navigate` (`/exploracion`) | Sin UI de marca; redirección. | n/a | n/a | Sin acción (redirección). |
| `/profile` | `ProfilePage` | Sin ocurrencias locales; usa shell global. | variable (shell) | si (solo shell) | Sin acción local. |
| `/payments/return` | `PaymentReturnPage` | Sin ocurrencias locales; usa shell global. | variable (shell) | si (solo shell) | Sin acción local. |
| `/certificates` | `CertificatesPage` | Sin ocurrencias locales; usa shell global. | variable (shell) | si (solo shell) | Sin acción local. |
| `/citizen-report` | `CitizenReportPage` | Sin ocurrencias locales; usa shell global. | variable (shell) | si (solo shell) | Sin acción local. |
| `/fires` | `Navigate` (`/fires/history`) | Sin UI de marca; redirección. | n/a | n/a | Sin acción (redirección). |
| `/fires/history` | `FireHistoryPage` | Sin ocurrencias locales; usa shell global. | variable (shell) | si (solo shell) | Sin acción local. |
| `/fires/:id` | `FireDetailPage` | Sin ocurrencias locales; usa shell global. | variable (shell) | si (solo shell) | Sin acción local. |
| `/login` | `LoginPage` | `BRAND.name` en header local (sin shell global por `hideChrome`). | variable | si | Sin acción local de texto plano. |
| `/register` | `RegisterPage` | `registerTitle` (`ForestGuard`, ES/EN) + `BRAND.name` (header y alt de imagen). | texto_plano (i18n) + variable | parcial | Parametrizar `registerTitle` con `{brandName}`. |
| `/auth/callback` | `AuthCallbackPage` | Sin ocurrencias locales; usa shell global. | variable (shell) | si (solo shell) | Sin acción local. |
| `/shelters` | `SheltersPage` | Sin ocurrencias locales; usa shell global. | variable (shell) | si (solo shell) | Sin acción local. |
| `/faq` | `FaqPage` | `faqSubtitle`, `faqQ1`, `faqA1`, `faqA2`, `faqA4`, `faqA5`, `faqQ6`, `faqA6`, `faqA7`, `faqQ8`, `faqA8`, `faqQ10`, `faqA10`, `faqA11`. | texto_plano (i18n) | no | Parametrizar claves con `{brandName}` y/o `{wildfireTerm}` según corresponda. |
| `/manual` | `ManualPage` | `manualSubtitle`, `manualGettingStartedP1`, `manualRegisterAccess1`, `manualRegisterAccess4`, `manualReportsP1`, `manualEpisodesP1`. | texto_plano (i18n) | no | Parametrizar claves con `{brandName}`, `{wildfireTerm}`, `{adminEmailDomain}`. |
| `/glossary` | `GlossaryPage` | `glossarySubtitle`, `glossaryDefLaw`, `glossaryDefHotspot`. | texto_plano (i18n) | no | Parametrizar claves con `{wildfireTerm}`. |
| `/contact` | `ContactPage` | Sin ocurrencias locales; usa shell global. | variable (shell) | si (solo shell) | Sin acción local. |
| `*` | `NotFoundPage` | Sin ocurrencias locales; usa shell global. | variable (shell) | si (solo shell) | Sin acción local. |

## 4. Claves i18n a parametrizar

| Clave | Locales con término | Ruta(s) / superficie | Término detectado | Placeholder objetivo |
| --- | --- | --- | --- | --- |
| `registerTitle` | ES + EN | `/register` | `ForestGuard` | `{brandName}` |
| `manualSubtitle` | ES + EN | `/manual` | `ForestGuard` | `{brandName}` |
| `manualGettingStartedP1` | ES + EN | `/manual` | `ForestGuard` + `wildfire` (EN) | `{brandName}`, `{wildfireTerm}` |
| `manualRegisterAccess1` | ES + EN | `/manual` | `ForestGuard` | `{brandName}` |
| `manualRegisterAccess4` | ES + EN | `/manual` | `@forestguard.ar` | `{adminEmailDomain}` |
| `manualReportsP1` | EN | `/manual` | `wildfires` | `{wildfireTerm}` |
| `manualEpisodesP1` | ES + EN | `/manual` | `ForestGuard` | `{brandName}` |
| `faqSubtitle` | EN | `/faq` | `wildfires` | `{wildfireTerm}` |
| `faqQ1` | ES + EN | `/faq` | `ForestGuard` + `wildfires` (EN) | `{brandName}`, `{wildfireTerm}` |
| `faqA1` | ES + EN | `/faq` | `ForestGuard` | `{brandName}` |
| `faqA2` | ES + EN | `/faq` | `ForestGuard` | `{brandName}` |
| `faqA4` | EN | `/faq` | `wildfires` | `{wildfireTerm}` |
| `faqA5` | ES + EN | `/faq` | `ForestGuard` | `{brandName}` |
| `faqQ6` | ES + EN | `/faq` | `ForestGuard` | `{brandName}` |
| `faqA6` | ES + EN | `/faq` | `ForestGuard` | `{brandName}` |
| `faqA7` | ES + EN | `/faq` | `ForestGuard` | `{brandName}` |
| `faqQ8` | ES + EN | `/faq` | `ForestGuard` | `{brandName}` |
| `faqA8` | ES + EN | `/faq` | `ForestGuard` | `{brandName}` |
| `faqQ10` | ES + EN | `/faq` | `ForestGuard` | `{brandName}` |
| `faqA10` | ES + EN | `/faq` | `ForestGuard` | `{brandName}` |
| `faqA11` | ES + EN | `/faq` | `ForestGuard` | `{brandName}` |
| `glossarySubtitle` | EN | `/glossary` | `wildfire` | `{wildfireTerm}` |
| `glossaryDefLaw` | EN | `/glossary` | `wildfires` | `{wildfireTerm}` |
| `glossaryDefHotspot` | EN | `/glossary` | `wildfires` | `{wildfireTerm}` |
| `fireFeed` | EN | `/home` | `Wildfire` | `{wildfireTerm}` |
| `footerBrandLine1` | EN | Footer | `wildfires` | `{wildfireTerm}` |
| `footerLeavingTitle` | ES + EN | Diálogo salida a externos | `ForestGuard` | `{brandName}` |
| `footerExternalDailyReportLabel` | EN | Footer/help links | `wildfire` | `{wildfireTerm}` |
| `footerExternalSnmfTooltip` | EN | Footer/public sources | `wildfire` | `{wildfireTerm}` |

Claves detectadas con términos de marca pero fuera de alcance principal por no renderizarse hoy:
- `loginWelcome`.
- `footerExternalDailyReportTooltip`.

## 5. Brechas respecto de `frontend/src/config/brand.ts`

Estado actual:
- `BRAND.name` ya se usa en superficies principales de marca.

Brechas abiertas para el rename final:
- Falta centralizar término funcional `wildfire/wildfires`.
- Falta centralizar dominio de admins (`@forestguard.ar`).
- Falta centralizar URL de docs (`/docs` con dominio actual hardcodeado en navegación).
- Falta centralizar SEO (`title` y `description`) que hoy está hardcodeado en `frontend/index.html`.
- Falta parametrización i18n por placeholders (`{brandName}`, `{wildfireTerm}`, `{adminEmailDomain}`).
- Persisten literales de marca en traducciones (`ForestGuard`) fuera de `BRAND`.

## 6. Contrato objetivo para rename final (single source)

```ts
BRAND = {
  name,
  terms: { wildfire: { es, en } },
  domains: { adminEmailDomain },
  links: { publicUrl, docsUrl, github },
  seo: { title: { es, en }, description: { es, en } }
}
```

Placeholders obligatorios en i18n:
- `{brandName}`
- `{wildfireTerm}`
- `{adminEmailDomain}`

Objetivo final:
- No debe quedar ningún `ForestGuard|Vestigia|Wildfire` hardcodeado en UI fuera de `brand.ts`.
- Los textos i18n deben consumir placeholders y resolver desde la configuración central.

## 7. Casos de prueba y escenarios de aceptación (del reporte)

- [ ] Cada ruta declarada en `frontend/src/App.tsx` figura en el inventario page-by-page.
- [ ] Toda coincidencia UI de `ForestGuard|Vestigia|Wildfire` en `frontend/src` + `frontend/index.html` está documentada.
- [ ] Cada fila está clasificada como `texto_plano` o `variable`.
- [ ] Cada fila indica si está centralizada en `brand.ts` (`si/no/parcial`).
- [ ] Existe lista explícita de brechas accionables para pasar a fuente única.

## 8. Supuestos y defaults aplicados

1. Alcance: solo UI renderizada.
2. Se consideran ES y EN cuando al menos una locale contiene término de marca.
3. `Wildfire/wildfires` se considera término de branding editable y se centraliza.
4. No se incluye en el inventario principal lo no renderizado actualmente (`loginWelcome`, `footerExternalDailyReportTooltip`) ni strings técnicos no visibles.
