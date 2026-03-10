# Plan repo-grounded de release android en google play (ForestGuard)

> Plan detallado de release Android. El estado actual de despliegue web/backend está en `docs/infrastructure/deployment/DEPLOYMENT.md`; usar este archivo como referencia específica para la pista Android/Play Store.

## Resumen
Objetivo: llevar el estado actual (web + backend) a un release Android publicable con AAB, cumpliendo políticas Play vigentes al **23-feb-2026**, con hardening de seguridad/privacidad, pipeline reproducible y checklist humano.

Resultado esperado al cerrar el plan:
1. Documento final en `docs/release/play_store_release_plan.md`.
2. 3 PRs técnicos separados (`compliance`, `security`, `release`) + PR-0 de decisiones humanas.
3. Build local/CI reproducible de `app-release.aab` firmado y validado.
4. Ruta clara para closed testing y publicación en producción.

## Diagnóstico actual (repo-grounded)
Estado confirmado en repo:
- No existe módulo Android ni Gradle Android en el proyecto.
- No existe configuración Capacitor (`capacitor.config.*`) ni dependencias `@capacitor/*`.
- No hay pipeline Android release en CI (solo build/push frontend).
- Backend ya contempla Android en pagos:
  - `app/api/v1/payments.py:69`
  - `app/api/v1/payments.py:108`
  - `app/api/v1/payments.py:147`
- URLs Android ya parametrizadas:
  - `.env.template:219`
  - `.env.template:220`
  - `.env.template:221`
- Frontend ya envía plataforma:
  - `frontend/src/hooks/mutations/useCreateCheckout.ts:38`
- Runbook menciona deep links Android, pero no existe app Android todavía:
  - `docs/development/runbooks/auth-validation.md:75`
- Riesgo actual de sesión/tokens en almacenamiento web:
  - `frontend/src/lib/supabase.ts:14`
  - `frontend/src/services/api.ts:60`
- Logs de cliente en flujos de pago a redaccionar:
  - `frontend/src/hooks/mutations/useCreateCheckout.ts:35`
  - `frontend/src/components/payments/PaymentButton.tsx:39`
- `init_plan.md` usa nombre de app incorrecto (`Vestigia`) en comando de init:
  - `docs/deployment/play_store/init_plan.md` (sección instructivo).

## Gaps vs requisitos Play (priorizados)
Bloqueantes:
- Falta Android shell/build system (no AAB posible).
- Falta configuración `compileSdk/targetSdk` y manifest Android.
- Falta firma release (upload key + Play App Signing).
- Falta flujo release reproducible local/CI.
- Falta plan operativo de closed testing para cuenta personal nueva.

Alta:
- OAuth móvil debe usar navegador externo (no embedded WebView) para evitar rechazo/política.
- Falta App Links verificados para producción (custom scheme solo como fallback).
- Falta hardening de storage de sesión/token para Android.
- Falta política formal de versionado (`versionCode`/`versionName`).

Media:
- Falta matriz explícita de dispositivos para closed testing.
- Falta proceso documentado de backup/rotación de upload key.
- Falta estrategia formal de hotfix (con/sin OTA JS).

## Decisiones cerradas para implementación
Decisiones ya fijadas:
- Stack Android: **Capacitor**.
- Firma: **Upload key + Play App Signing**.
- Tipo de cuenta: **personal nueva**.
- PR-1 bloqueado hasta definir identidad final.

Decisión externa pendiente (bloqueante absoluto de PR-1):
- `applicationId` definitivo y nombre final de app.
- Política: no iniciar `npx cap init` ni crear app en Play con identificador temporal.

Default técnico definido para destrabar diseño:
- Producción: **Android App Links (https + assetlinks.json)**.
- Fallback en desarrollo/controlado: `forestguard://...`.
- OAuth Android: navegador externo mediante `@capacitor/browser` (no WebView embebido).

## Corrección normativa importante (23-feb-2026)
Requisito oficial de personal accounts (creadas después del 13-nov-2023): **closed test con al menos 12 testers opt-in durante 14 días continuos**, luego solicitud de acceso a producción. No se encontró requisito oficial de “20 aceptaciones” en la documentación oficial consultada.

## Mapa de Build & Release (comandos, inputs, outputs)

### Estado objetivo local (PowerShell)
1. Precondición de identidad:
```powershell
$env:APP_NAME="ForestGuard"            # o definitivo
$env:APP_ID="com.forestguard.app"      # definitivo, inmutable tras publicar
```

2. Bootstrap Android (una sola vez):
```powershell
cd c:\Users\nicog\wildfire-recovery-argentina\frontend
npm ci
npm install @capacitor/core @capacitor/cli @capacitor/android @capacitor/browser
npx cap init "$env:APP_NAME" "$env:APP_ID" --web-dir=dist
npx cap add android
```

3. Build web + sync nativo:
```powershell
npm run build
npx cap sync android
```

4. Build release AAB firmado:
```powershell
cd .\android
.\gradlew.bat clean :app:bundleRelease
```

5. Validación bundle:
```powershell
java -jar ..\..\tools\bundletool-all.jar validate --bundle .\app\build\outputs\bundle\release\app-release.aab
```

Inputs obligatorios:
- `APP_ID`, `APP_NAME`.
- Keystore y `keystore.properties` fuera de git.
- Variables de entorno Android auth/deep links.

Output final:
- `frontend/android/app/build/outputs/bundle/release/app-release.aab`.

## Plan por PRs (decision-complete)

## PR-0 (humano, sin código) — Gate de identidad y operación Play
Objetivo:
- Definir `applicationId` y nombre final.
- Crear app en Play Console con esos valores.
- Definir owner/respaldo de upload key y calendario de testing.

Entregables:
- Registro de decisión en `docs/release/play_store_release_plan.md`.
- Matriz inicial de testers (mínimo 12 activos objetivo; ideal 20 reclutados por riesgo operativo).
- Ventana de testing y owner por track.

Criterio de salida:
- Identidad app cerrada y publicada en documento; PR-1 desbloqueado.

## PR-1 (Compliance Android Base)
Objetivo:
- Crear shell Android y cumplir baseline técnico Play.

Cambios de archivos (nuevos/editados):
- `frontend/capacitor.config.ts`
- `frontend/package.json` (scripts android)
- `frontend/android/**` (proyecto nativo)
- `frontend/android/app/build.gradle`
- `frontend/android/build.gradle`
- `frontend/android/gradle.properties`
- `frontend/android/app/src/main/AndroidManifest.xml`
- `frontend/android/app/src/main/res/xml/network_security_config.xml`
- `frontend/scripts/validate-build-env.mjs` (aceptar rutas Android válidas)
- `docs/release/play_store_release_plan.md` (sección compliance)

Requisitos técnicos en PR-1:
- `compileSdk=35`, `targetSdk=35`, `minSdk=24`.
- `usesCleartextTraffic=false`, TLS only.
- Permisos mínimos: `INTERNET`, `ACCESS_NETWORK_STATE`.
- Deep links:
  - App Links `https://...` verificados (manifest + assetlinks).
  - fallback `forestguard://...` solo no-producción.
- AAB release con signing config por `keystore.properties` no versionado.

Criterio de salida:
- `:app:bundleRelease` exitoso y `bundletool validate` OK.
- Manifest sin componentes exportados inseguros.

## PR-2 (Seguridad y Privacidad Hardening)
Objetivo:
- Endurecer auth/session, logging y deep links.

Cambios de archivos (nuevos/editados):
- `frontend/src/lib/supabase.ts`
- `frontend/src/services/api.ts`
- `frontend/src/context/AuthContext.tsx` (si aplica en repo actual)
- `frontend/src/hooks/mutations/useCreateCheckout.ts`
- `frontend/src/components/payments/PaymentButton.tsx`
- `frontend/src/test/validate-build-env.test.ts`
- `frontend/android/app/src/main/java/**` (bridge/plugin secure storage)
- `docs/release/play_store_release_plan.md` (threat model + data safety map)

Hardening mínimo:
- Storage Android con cifrado de credenciales/sesión (EncryptedSharedPreferences via plugin).
- Eliminar/redactar logs sensibles de pagos/auth.
- Validación estricta de redirect URI y origen.
- Política explícita de permisos sensibles (si no se usan, no declararlos).

Criterio de salida:
- Tests unitarios de validación env/deep links en verde.
- No secrets hardcodeados en cliente Android/web.
- Threat model corto documentado.

## PR-3 (Release Reproducible + CI/CD + Operación Play)
Objetivo:
- Automatizar build firmado AAB y checklist de publicación.

Cambios de archivos (nuevos/editados):
- `.github/workflows/android-release.yml`
- `frontend/scripts/android_build_release.ps1`
- `docs/release/play_store_release_plan.md` (instructivo final + checklist)
- Opcional: `docs/release/play_store_data_safety_map.md`

Pipeline `android-release.yml`:
- Gates previos: `gitleaks`, `npm audit`, `pip-audit` (reusar o encadenar con workflow existente).
- Build web.
- `cap sync android`.
- `:app:bundleRelease` firmado.
- `bundletool validate`.
- Publicar artefacto AAB + `SHA256`.
- Versionado:
  - `versionName`: SemVer desde tag `vMAJOR.MINOR.PATCH`.
  - `versionCode`: entero monotónico desde `GITHUB_RUN_NUMBER` (obligatorio en release).

Criterio de salida:
- Workflow reproducible en main/tag sin pasos manuales ocultos.
- AAB descargable, hash publicado, checklist completo.

## Cambios en interfaces públicas (API/env/tipos)
- Variables frontend nuevas:
  - `VITE_AUTH_REDIRECT_URL_ANDROID`
  - `VITE_DEEP_LINK_SCHEME`
  - `VITE_APP_LINK_HOST`
- Contrato backend de pagos:
  - Se mantiene `client_platform: 'web' | 'android'` sin breaking change.
- Build interface:
  - scripts nuevos: `android:sync`, `android:build:aab`, `android:bundle:validate`.

## Threat model corto
Activos:
- JWT/refresh token, sesión, estado de pago, identidad de usuario, integridad del binario firmado.

Amenazas:
- Exfiltración token (XSS/storage inseguro).
- Hijack de deep links por custom scheme.
- MITM/cleartext.
- Rechazo OAuth por embedded user-agent.
- Compromiso/pérdida de upload key.

Mitigaciones:
- Secure storage Android + sanitización logs.
- App Links verificados + custom scheme solo fallback.
- `network_security_config` TLS only.
- OAuth en navegador externo con `@capacitor/browser`.
- Play App Signing + política de backup/rotación upload key.

## Estrategia de versionado y hotfix
Versionado (obligatorio):
- `versionName`: SemVer (`MAJOR.MINOR.PATCH`), fuente tag git.
- `versionCode`: monotónico CI.
- Reglas:
  - `PATCH`: fixes sin cambios de contrato.
  - `MINOR`: funcionalidades compatibles.
  - `MAJOR`: cambios incompatibles.

Hotfix policy (cerrada):
- GA inicial sin OTA JS.
- Hotfix urgente:
  - Si afecta JS/UI no nativo: release acelerado Play en track cerrado/interno.
  - Evaluación post-GA de live updates (Capgo/Appflow) bajo revisión de seguridad y gobernanza.

## Closed testing plan operativo
Cronograma sugerido desde **23-feb-2026**:
- Semana 1: PR-0 + reclutamiento testers + app setup Play.
- Semana 2-3: PR-1/PR-2 y entrada a closed testing.
- Semana 3-5: 14 días continuos con 12 testers opt-in.
- Semana 5-6: solicitud acceso producción + revisión (usualmente <=7 días según Play para ese paso).

Matriz mínima de dispositivos (12 testers):
- API: 24, 28, 33, 35.
- OEM: Samsung, Xiaomi/POCO, Motorola, Pixel.
- Tamaños: compacto, normal, grande.
- Red: WiFi/4G/5G intermitente para smoke de auth/pagos.

Criterios de salida testing:
- Crash-free sesiones > 99%.
- ANR dentro de umbrales Android Vitals.
- Flujos críticos OK: login, refresh sesión, checkout, retorno deep link/app link.

## Test cases y aceptación técnica
- `npm run build` + `npx cap sync android` sin errores.
- `.\gradlew.bat :app:bundleRelease` genera AAB firmado.
- `bundletool validate` pasa.
- Validación deep links:
  - `https://...` abre app por App Links verificado.
  - `forestguard://...` funciona en dev fallback.
- OAuth smoke: login/redirect de ida y vuelta sin WebView embebido.
- Pago smoke: checkout + retorno con estado.
- Security checks:
  - `gitleaks` sin hallazgos.
  - `npm audit --omit=dev` sin high/critical.
  - `pip-audit` en CI sin bloqueantes.

## Checklist humano Play Console
- Crear/confirmar app con nombre final y `applicationId` definitivo.
- Activar Play App Signing.
- Subir AAB firmado con upload key.
- Completar Data Safety + política de privacidad.
- Declarar permisos usados y justificación.
- Configurar closed testing y mantener 12 testers opt-in 14 días continuos.
- Aplicar a producción al completar criterio.
- Rollout gradual: 10% -> 50% -> 100%.
- Monitorear vitals/crashes en primeras 72 horas.
- Registrar evidencia release: SHA git, SHA256 AAB, run CI, formulario checklist.

## Supuestos y defaults explícitos
- PR-1 permanece bloqueado hasta decisión externa de identidad (`APP_ID`, nombre app).
- Se mantiene backend actual sin cambios breaking.
- No se añade iOS al alcance.
- Commits firmados se aplican si branch policy lo exige.
- Revisión regulatoria se revalida antes de enviar a Play si pasan más de 30 días desde este plan.

## Fuentes normativas usadas (verificadas al 23-feb-2026)
- Target API requirements: https://support.google.com/googleplay/android-developer/answer/11926878?hl=en
- Closed testing personal accounts: https://support.google.com/googleplay/android-developer/answer/14151465?hl=en
- App Bundles requirement/guidance: https://developer.android.com/appbundle
- 64-bit support guidance: https://developer.android.com/google/play/requirements/64-bit
- App Links y `assetlinks.json`: https://developer.android.com/training/app-links/configure-assetlinks
- OAuth native apps / embedded user-agent restrictions: https://developers.google.com/identity/protocols/oauth2/native-app
- Capacitor Browser plugin docs: https://capacitorjs.com/docs/apis/browser
- Play App Signing / upload key reset: https://developer.android.com/studio/publish/app-signing
