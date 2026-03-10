# Guia maestra de despliegue de ForestGuard

Este documento actúa como índice canónico de **todas las rutas de despliegue soportadas** para ForestGuard. Desde aquí se puede navegar a los runbooks específicos y al plan vigente de Android/Play Store.

---

## 1. Introducción y alcance

- **Alcance**:
  - Despliegue en VM Oracle Cloud usando Docker Compose y `scripts/deploy.sh`.
  - Flujos de CI/CD en GitHub Actions.
  - Escenarios de troubleshooting y quick fixes.
  - Visión de la pista Android / Google Play (plan vigente separado).
- **Entornos cubiertos**:
  - Desarrollo local.
  - Producción en VM (Oracle Cloud, actual).
  - Entornos futuros (staging/preprod) pueden añadirse como extensiones de este documento.

---

## 2. Matriz de entornos y topología

| Entorno          | Objetivo principal                       | Herramientas clave                        | Referencias                                       |
|------------------|------------------------------------------|-------------------------------------------|--------------------------------------------------|
| Local dev        | Desarrollo y debug                       | `docker compose`, `.env` local            | Sección 4; `docs/architecture/containers.md`     |
| Producción (VM)  | Servicio público ForestGuard             | Docker Compose, `scripts/deploy.sh`, CI   | Sección 3; `docs/architecture/containers.md`     |
| Android / Play   | App Android (Capacitor + AAB, futuro)    | Capacitor, Gradle, Play Console           | Sección 6; `docs/deployment/play_store/revised_plan.md` |

- **Topología de servicios**: la composición de contenedores (API, frontend, workers, Redis, nginx, certbot, etc.) está descrita en detalle en `docs/architecture/containers.md`.

---

## 3. Despliegue en producción (VM Docker Compose)

### 3.1 Prerrequisitos de VM

- VM Linux (Oracle Cloud) con:
  - Docker y Docker Compose instalados.
  - Dominio y SSL configurados.
  - Archivo `.env` en la VM con claves reales (no versionado en el repo).
  - Repo clonado en `/home/opc`.

### 3.2 Flujo operativo recomendado (automatizado)

1. Hacer push y merge a `main`.
2. El workflow de deploy (`.github/workflows/deploy-prod-vm.yml`) ejecuta SSH a la VM.
3. En la VM se ejecuta:
   - `git pull --ff-only`
   - `./scripts/deploy.sh`
4. Healthcheck básico:
   - `curl -L http://localhost/health`

### 3.3 Scripts clave

- `scripts/deploy.sh`:
  - Orquestra `docker compose` para levantar/actualizar todos los servicios definidos en `docker-compose.yml`.
  - Soporta rebuild selectivo de servicios (por ejemplo, solo frontend) según flags definidos en el script.
- Scripts de SSL:
  - `scripts/setup-ssl.sh`, `scripts/renew-ssl.sh`, `scripts/renew-ssl-cron.sh`, `scripts/verify-ssl.sh` gestionan certificados y renovación.

Para comandos detallados, pasos manuales y escenarios extendidos de despliegue en VM, ver:

- `docs/infrastructure/deployment/quick-deployment-commands.md`

---

## 4. Despliegue local y validación rápida

### 4.1 Levantar stack local mínimo

```bash
docker compose up -d
```

### 4.2 Servicios esperados en local

- API: `http://localhost:8000/docs`
- Frontend: `http://localhost:5173`

### 4.3 Casos de uso de entorno local

- Reproducir issues de producción en un entorno controlado.
- Validar cambios de código antes de desplegar.
- Ejecutar pruebas manuales de flujos críticos (login, carrusel, mapas, etc.).

---

## 5. CI/CD de despliegue

### 5.1 Workflows relevantes

- `.github/workflows/deploy-prod-vm.yml`:
  - **Propósito**: automatizar el despliegue a la VM de producción.
  - **Trigger típico**: merges a `main` (y/o tags definidas en el workflow).
  - **Acciones principales**:
    - Conectar por SSH.
    - Ejecutar `git pull --ff-only` y `scripts/deploy.sh`.

- Otros workflows de build y publicación de imágenes (por ejemplo, multi-arquitectura para frontend) se describen en:
  - `docs/infrastructure/deployment/immediate-fix.md` (contexto multi-arch AMD64/ARM64).

### 5.2 Contratos de CI

- Antes de que se dispare un deploy a producción, se espera:
  - Tests y linters en verde.
  - Build de imágenes Docker exitoso.
  - Sin vulnerabilidades críticas/bloqueantes en los pasos de seguridad (según políticas de CI).
- Convenciones de imágenes:
  - Imágenes publicadas en GHCR (`ghcr.io/nicolasgh91/wildfire-recovery-argentina/...`).
  - Tagging consistente (por ejemplo, `latest` y tags derivados de versiones/git SHA).

---

## 6. Pista Android / Google Play (visión de alto nivel)

Actualmente **no existe módulo Android** en este repositorio; el despliegue Android/Play Store aún no está implementado a nivel de código, pero sí existe un plan técnico detallado.

- **Plan vigente de pista Android/Play Store**:
  - Documento: `docs/deployment/play_store/revised_plan.md`
  - Alcance:
    - Crear shell Android con Capacitor.
    - Generar AAB firmado y validado.
    - Cumplir requisitos Play (Target API 35+, 64‑bit, closed testing 12 testers/14 días, etc.).
    - Integrar una pista de CI/CD `android-release.yml` para build y validación de bundles.

- **Uso de este documento**:
  - Utilizar `DEPLOYMENT.md` para entender cómo se integrará Android en la estrategia general de despliegue.
  - Ir a `docs/deployment/play_store/revised_plan.md` para el diseño detallado (PRs, comandos, matrices de testing y threat model).

El plan previo de Android (histórico) se conserva en:

- `docs/archive/deployment/init_plan_android_play_store.md` — documento original, que delega en el plan vigente anterior.

---

## 7. Troubleshooting y quick fixes

### 7.1 Diagnóstico rápido (VM)

Comandos mínimos recomendados:

```bash
# estado de contenedores
docker compose ps

# logs relevantes
docker compose logs --tail=100 api
docker compose logs --tail=100 frontend
docker compose logs --tail=100 nginx

# health local en VM
curl -L http://localhost/health
```

### 7.2 Problemas frecuentes

Para diagnósticos más profundos y soluciones específicas, ver:

- `docs/infrastructure/deployment/quick-fixes.md` — problemas frecuentes (nginx, frontend, API, SSL, recursos, memoria, etc.) con comandos concretos.
- `docs/infrastructure/deployment/immediate-fix.md` — fix específico para desajustes de arquitectura (imágenes ARM64 vs AMD64) y build multi-arch.

### 7.3 Procedimientos de emergencia

`quick-fixes.md` define procedimientos de emergencia para escenarios como:

- Sitio completamente caído (diagnóstico y restart completo de servicios).
- Reinicios selectivos de frontend/nginx o backend.
- Ajustes de memoria (swap) en VMs pequeñas.

Se recomienda revisar ese documento antes de intervenir manualmente la infraestructura.

---

## 8. Referencias completas

- `docs/architecture/containers.md` — topología de contenedores, workers y colas.
- `docs/infrastructure/deployment/quick-deployment-commands.md` — comandos manuales de despliegue y orquestación detallados.
- `docs/infrastructure/deployment/quick-fixes.md` — guía de troubleshooting para problemas frecuentes.
- `docs/infrastructure/deployment/immediate-fix.md` — solución multi‑arquitectura para imágenes Docker de frontend.
- `docs/deployment/play_store/revised_plan.md` — plan vigente de Android/Play Store (diseño detallado de la pista).
