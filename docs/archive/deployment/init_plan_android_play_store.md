
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
...
(resto del documento original mantenido aquí como plan histórico para Android/Play Store; el plan vigente y consolidado vive en `docs/deployment/play_store/revised_plan.md`.)

