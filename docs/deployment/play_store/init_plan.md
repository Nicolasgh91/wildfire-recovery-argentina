
Plan

Plan Repo-Grounded para Publicar en Google Play (Android) con Capacitor + AAB
Resumen
Objetivo: llevar el repo actual (web React + FastAPI) a un release Android publicable en Play Store con AAB firmado, cumplimiento técnico (API 35+, 64-bit), hardening de seguridad/privacidad, y guía reproducible para humano/CI.
Estrategia cerrada: Capacitor, Play App Signing + upload key, cuenta personal nueva (incluye closed testing 12 testers / 14 días), esquema de deep link forestguard://.
Bloqueante pendiente: definir applicationId definitivo (package name) antes de cerrar PR de compliance.

Diagnóstico Actual (Repo-Grounded)
Hallazgo	Evidencia	Impacto
No existe proyecto Android en el repo	NO_ANDROID_BUILD_FILES_FOUND (búsqueda en git ls-files)	Bloqueante: hoy no se puede generar AAB/APK
No existe configuración Capacitor	NO_CAPACITOR_FILES_FOUND + sin @capacitor en package.json	Bloqueante: falta shell Android
No hay PWA manifest/service worker	NO_PWA_MANIFEST_OR_SW_FOUND	No hay alternativa TWA lista
El backend ya contempla plataforma Android en pagos	payments.py (line 69), payments.py (line 107), payments.py (line 108)	Base útil para deep links de retorno
El frontend ya envía client_platform	useCreateCheckout.ts (line 34)	Base útil para checkout Android
El build validator hoy bloquea redirect custom scheme	validate-build-env.mjs (line 61)	Gap directo contra deep links forestguard://...
El runbook propone deep links Android pero no hay app Android	auth-validation.md (line 73)	Desalineación doc vs implementación real
Sesión/tokens en localStorage	supabase.ts (line 14), api.ts (line 60)	Riesgo de exfiltración por XSS en entorno híbrido
Hay logs de flujo de pago en cliente	useCreateCheckout.ts (line 35), PaymentButton.tsx (line 39)	Riesgo de exposición operativa/PII en logs
CSP sigue en report-only con unsafe-inline/unsafe-eval	nginx.conf (line 38)	Hardening web incompleto
CI actual solo build/push de frontend Docker	frontend-build.yml (line 30)	No existe pipeline Android release
Dependencias frontend sin vulns prod en auditoría local	npm audit --omit=dev --json => 0	Buen punto de partida para JS
pip-audit no disponible localmente	comando local falló por módulo faltante	Evidencia Python incompleta fuera de CI
Documento previo afirma “ready for Play” pero sin módulo Android real	SECURITY_IMPROVEMENTS_SUMMARY.md (line 385)	Señal documental desactualizada para release Android real
Gaps vs Requisitos Play (Prioridad)
Requisito Play	Estado actual	Gap concreto	Prioridad
Target API 35+	No existe Gradle Android	Configurar compileSdk=35, targetSdk=35	Bloqueante
Closed testing (12/14 para cuenta personal nueva)	Sin pipeline Play	Definir track closed testing + grupos + cronograma	Bloqueante
64-bit obligatorio	No existe build Android	Verificar artefacto arm64 y configuración ABI	Bloqueante
Release en AAB	Sin Android module ni firma	Generar bundleRelease + signing seguro + validación bundletool	Bloqueante
Permisos/manifest seguros	No existe AndroidManifest.xml app	Declarar permisos mínimos y exported rules	Alta
Seguridad de red Android	Sin network_security_config.xml	Forzar TLS-only y bloquear cleartext	Alta
Gestión segura de sesión/token móvil	localStorage	Implementar secure storage nativo en Android	Alta
Dependencias y licencias	Sin SBOM/license check	Agregar licencia/SBOM gate en CI	Media
Fase 0 — Mapa de Build & Release
Estado actual (web, hoy)
Paso	Comando	Inputs	Output
Build frontend	npm run build	env frontend (VITE_*)	frontend/dist
Validación env (Docker build)	validate-build-env.mjs	VITE_AUTH_REDIRECT_URL, VITE_SUPABASE_*	Pass/fail build
Imagen frontend	workflow frontend-build.yml	secrets GH + Dockerfile	imagen GHCR multi-arch
Estado objetivo (android, a implementar)
Paso	Comando	Inputs	Output
Build web assets para Capacitor	npm run build	.env.android	frontend/dist
Sync Android shell	npx cap sync android	capacitor.config.* + dist	proyecto frontend/android actualizado
Build release AAB	gradlew.bat :app:bundleRelease	keystore + gradle signing config	app-release.aab
Validación bundle	bundletool validate --bundle ...	AAB	validación técnica
Smoke en dispositivo/emulador	bundletool build-apks + install-apks	AAB + keystore	app instalable para smoke
PR Plan (separado por tema)
PR-1 Compliance Android Base (Bloqueante)
Objetivo: crear app Android funcional en Capacitor y cumplir baseline Play técnico.

Cambios:

Crear capacitor.config.ts.
Crear proyecto frontend/android con npx cap add android.
Configurar SDK y versión en Gradle: compileSdk=35, targetSdk=35, minSdk=24, versionCode, versionName.
Configurar signing release con keystore.properties no versionado y lectura segura en Gradle.
Agregar network_security_config.xml y referenciarlo en manifest.
Definir manifest mínimo con permisos estrictos (INTERNET, ACCESS_NETWORK_STATE) y android:usesCleartextTraffic="false".
Configurar deep links forestguard://auth/callback y forestguard://payments/return.
Añadir scripts npm: android:sync, android:build:aab, android:bundle:validate.
Añadir doc técnica inicial en play_store_release_plan.md con estado “PR1”.
Commits sugeridos:

feat(android): bootstrap capacitor project and gradle release baseline
feat(android): enforce api35 tls-only manifest and deep links
PR-2 Seguridad y Privacidad (Hardening)
Objetivo: reducir superficie de ataque móvil/web híbrida.

Cambios:

Reemplazar lectura directa de token en localStorage para Android con almacenamiento seguro nativo (plugin propio Capacitor basado en EncryptedSharedPreferences).
Introducir interfaz de storage de sesión para separar web vs android.
Ajustar validate-build-env.mjs para aceptar redirect Android con esquema forestguard:// y cubrir casos válidos de parsing.
Actualizar tests en validate-build-env.test.ts.
Reducir/retirar logs de pago sensibles en cliente (useCreateCheckout, PaymentButton).
Endurecer validación de redirect en AuthContext para esquemas móviles.
Crear threat model corto en play-android-threat-model.md.
Documentar permisos y Data Safety map en play_store_release_plan.md.
Commits sugeridos:

feat(security): add secure session storage for android
chore(security): harden redirect validation and redact payment logs
docs(security): add play android threat model
PR-3 Release Reproducible + Play Console
Objetivo: cerrar pipeline de release y checklist humano de publicación.

Cambios:

Crear android-release.yml para build AAB firmado y artefacto descargable.
Añadir validación de keystore/secrets en CI.
Ejecutar validación bundletool en CI.
Crear script local reproducible android_build_release.ps1.
Completar play_store_release_plan.md con diagnóstico final, gaps cerrados, comandos copy/paste y checklist Play.
Incluir plan de closed testing (12 testers/14 días) con hitos y criterios de salida.
Verificar política de commits firmados y aplicar en PRs si repositorio lo requiere.
Commits sugeridos:

ci(android): add signed aab release workflow
docs(release): add complete play store release plan and checklist
Cambios en APIs/Interfaces/Tipos Públicos
Componente	Cambio	Compatibilidad
Frontend env vars	Añadir VITE_AUTH_REDIRECT_URL_ANDROID y VITE_DEEP_LINK_SCHEME	Backward compatible (web mantiene actuales)
Frontend checkout payload	Mantener `client_platform: 'web'	'android'`
Backend payments	Mantener rutas y contrato actual; solo endurecer validación de URLs por plataforma	Sin breaking change
Build interfaces	Nuevos comandos npm para Android build/release	No afecta runtime API
Threat Model Corto (Activos, Amenazas, Mitigaciones)
Activo	Amenaza principal	Mitigación existente	Mitigación a implementar
JWT/session	Robo por XSS/localStorage	PKCE y refresh session	Secure storage Android + reducir exposición token en cliente
Flujo de pago	Manipulación de retorno/deep link	payment_request_id y estado backend	Validación estricta deep link + smoke tests e2e de retorno
Tráfico app->API	MITM/cleartext downgrade	HTTPS en URLs productivas	network_security_config + cleartext deshabilitado
Datos de usuario en logs	Exposición accidental	Logs de servidor controlados	Redacción/eliminación de logs cliente sensibles
Integridad release	Keystore leakage	Secretos fuera de repo	Play App Signing + secretos CI + keystore no versionado
Test Cases y Escenarios de Aceptación
validate-build-env.test.ts debe pasar con casos web y Android scheme.
gradlew.bat :app:lintRelease debe pasar sin warnings bloqueantes de seguridad.
gradlew.bat :app:bundleRelease debe generar AAB firmado reproducible.
bundletool validate --bundle app-release.aab debe finalizar OK.
Smoke auth: login OAuth y retorno a /auth/callback vía deep link Android.
Smoke pagos: checkout externo y retorno forestguard://payments/return con estado correcto.
Verificación de ABI/64-bit: confirmar presencia de binarios compatibles y aceptación Play.
npm audit --omit=dev debe permanecer sin high/critical.
CI Python debe ejecutar pip-audit (gate obligatorio en pipeline central).
Escaneo de secretos en CI (gitleaks) debe quedar en verde.
Instructivo Reproducible (Copy/Paste, local)
# 0) Bloqueante: definir APP_ID antes de empezar
$env:APP_ID = "<PENDIENTE.definir.applicationId>"

# 1) Frontend build
cd c:\Users\nicog\wildfire-recovery-argentina\frontend
npm ci
npm run build

# 2) Bootstrap Capacitor Android (una vez)
npm install @capacitor/core @capacitor/cli @capacitor/android
npx cap init "Vestigia" $env:APP_ID --web-dir=dist
npx cap add android

# 3) Sync cambios web->android
npx cap sync android

# 4) Build AAB release
cd .\android
.\gradlew.bat clean :app:bundleRelease

# 5) Validación bundletool
# Requiere bundletool jar local, ej: tools\bundletool-all.jar
java -jar ..\..\tools\bundletool-all.jar validate --bundle .\app\build\outputs\bundle\release\app-release.aab
Checklist Humano Play Console
Crear app en Play Console con nombre final y applicationId definitivo.
Subir AAB release firmado (upload key) y habilitar Play App Signing.
Completar Data Safety (auth, pagos, analítica si aplica) y política de privacidad.
Declarar permisos realmente usados y justificar cada uno.
Configurar closed testing track.
Cargar al menos 12 testers válidos y sostener 14 días de actividad.
Verificar crash-free basic smoke y métricas de ANR antes de producción.
Revisar contenido legal/comercial (clasificación, contacto, país, precios).
Publicar en producción solo tras cerrar hallazgos bloqueantes/altos de PR2.
Guardar evidencia de release (commit SHA, AAB hash, workflow run, checklist firmado).
Supuestos y Defaults Explícitos
Se usa Capacitor como base Android.
Modelo de firma: Upload key + Play App Signing.
Cuenta Play: personal nueva, con requisito de closed testing 12 testers / 14 días.
Esquema deep link estándar: forestguard://.
applicationId queda pendiente de definición y es bloqueante para merge de PR-1.
No se pide soporte iOS en este alcance.
Se mantienen contratos backend existentes sin breaking changes.
Se exigirá commit firmado solo si la política del repo/branch lo requiere.
