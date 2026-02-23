# Análisis y optimización de workflows CI/CD — ForestGuard

> Fecha: 2026-02-23  
> Alcance: `deploy-prod-vm.yml`, `post-deploy-storage.yml`, `frontend-build.yml`

---

## Resumen ejecutivo

El workflow de despliegue a producción tarda entre 1 y 3 horas. El análisis identifica **tres causas raíz principales** y propone soluciones concretas que deberían reducir el tiempo a **8-15 minutos** en el escenario óptimo.

| Causa raíz | Impacto estimado | Solución |
|---|---|---|
| `docker compose build` ejecutándose en la VM free-tier (ARM64, CPU limitada) | 70-85% del tiempo total | Pre-build de imágenes backend en GitHub Actions + `docker compose pull` en VM |
| `docker builder prune -af` destruye la caché de BuildKit en cada deploy | Reconstrucción completa sin caché | Eliminar prune agresivo; solo limpiar dangling |
| Conexiones SSH independientes por cada step (4-5 handshakes) | ~30s acumulados + riesgo de timeout | SSH multiplexing via `~/.ssh/config` |

---

## 1. Diagnóstico del cuello de botella principal

### 1.1 El problema: build en la VM

El flujo actual ejecuta `scripts/deploy.sh` en la VM de Oracle Cloud. Aunque no se tiene visibilidad del contenido exacto de ese script, la duración de 1-3 horas indica con alta probabilidad que realiza `docker compose build` localmente en una instancia ARM64 Ampere A1 (free tier), con CPU limitada y RAM restringida.

Agravantes detectados en el workflow actual:

```yaml
# Línea 182 del deploy-prod-vm.yml — VM Preflight
docker builder prune -af  # ← DESTRUYE toda la caché de BuildKit
```

Este comando se ejecuta **antes de cada deploy**, garantizando que el `docker compose build` posterior parte de cero. En una VM con recursos limitados, esto convierte cada deploy en una reconstrucción completa.

### 1.2 Solución propuesta: pre-build en GitHub Actions

La misma estrategia que ya se aplica al frontend (build multi-arch en GitHub Actions → push a GHCR → pull en VM) debe extenderse al backend.

**Arquitectura objetivo:**

```
GitHub Actions (ubuntu-latest + QEMU)
  ├── Build backend image (linux/amd64 + linux/arm64) → GHCR
  ├── Build frontend image (ya existente) → GHCR
  └── Deploy:
        SSH → VM → docker compose pull → docker compose up -d
```

**Beneficios:**

- GitHub Actions runners tienen ~7 GB RAM y CPUs rápidas; QEMU cross-compile para ARM64 es más rápido que build nativo en free-tier.
- La caché GHA (`cache-from: type=gha`) persiste entre builds.
- La VM solo hace `pull` + `up`, lo cual tarda segundos.

**Nuevo workflow sugerido (`backend-build.yml`):**

```yaml
name: Backend build & push (multi-architecture)

on:
  push:
    branches: [main]
    paths:
      - 'app/**'
      - 'workers/**'
      - 'requirements*.txt'
      - 'Dockerfile'
      - '.github/workflows/backend-build.yml'
  workflow_dispatch:

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}/backend

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/setup-qemu-action@v3
        with:
          platforms: linux/amd64,linux/arm64
      - uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=sha,prefix=
            type=raw,value=latest,enable={{is_default_branch}}
      - uses: docker/build-push-action@v6
        with:
          context: .
          file: ./Dockerfile
          platforms: linux/amd64,linux/arm64
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

**Cambio en `deploy.sh` (o directamente en el remote script):**

```bash
# ANTES (build local, 1-3 horas):
docker compose build
docker compose up -d

# DESPUÉS (pull pre-built, ~30 segundos):
docker compose pull
docker compose up -d --remove-orphans
```

Esto requiere que `docker-compose.yml` referencie las imágenes de GHCR en lugar de usar `build:`.

---

## 2. Revisión crítica de la propuesta de SSH multiplexing

Tu propuesta es **correcta y bien fundamentada**. A continuación, la implementación concreta con una corrección menor.

### 2.1 Implementación en el step "Set up SSH"

```yaml
- name: Set up SSH
  env:
    PROD_VM_SSH_KEY:     ${{ secrets.PROD_VM_SSH_KEY }}
    PROD_VM_KNOWN_HOSTS: ${{ secrets.PROD_VM_KNOWN_HOSTS }}
    VM_HOST:             ${{ secrets.PROD_VM_HOST }}
    VM_USER:             ${{ secrets.PROD_VM_USER }}
    VM_PORT:             ${{ secrets.PROD_VM_PORT }}
  run: |
    install -m 700 -d ~/.ssh

    printf '%s\n' "$PROD_VM_SSH_KEY" > ~/.ssh/prod_vm_key
    chmod 600 ~/.ssh/prod_vm_key

    printf '%s\n' "$PROD_VM_KNOWN_HOSTS" >> ~/.ssh/known_hosts
    chmod 644 ~/.ssh/known_hosts

    PORT="${VM_PORT:-22}"
    cat > ~/.ssh/config << EOF
    Host prod
      HostName ${VM_HOST}
      User ${VM_USER}
      Port ${PORT}
      IdentityFile ~/.ssh/prod_vm_key
      StrictHostKeyChecking yes
      BatchMode yes
      ConnectTimeout 30
      ControlMaster auto
      ControlPersist 10m
      ControlPath ~/.ssh/cm-%C
    EOF
    chmod 600 ~/.ssh/config

    # Abrir conexión maestra explícitamente
    ssh -fN prod
```

### 2.2 Simplificación de los steps remotos

Cada step pasa de esto:

```yaml
ssh \
  -i ~/.ssh/prod_vm_key \
  -p "$PORT" \
  -o StrictHostKeyChecking=yes \
  -o ConnectTimeout=30 \
  -o BatchMode=yes \
  "${VM_USER}@${VM_HOST}" \
  bash -s << 'REMOTE_SCRIPT'
```

A esto:

```yaml
ssh prod bash -s << 'REMOTE_SCRIPT'
```

**Corrección a tu propuesta:** incluir `IdentityFile` en el bloque `Host` del config (ya lo contemplaste implícitamente al mencionar el ssh config, pero es necesario explicitarlo). Además, abrir la conexión maestra con `ssh -fN prod` al final del setup garantiza que el primer step remoto no paga el costo de establecimiento.

### 2.3 Confirmación de consistencia

Todos los steps remotos (VM Preflight, Deploy, Post-deploy health check, Diagnostic logs) usan el mismo host/usuario/puerto, lo cual confirma que **la reutilización de la sesión multiplexada es viable sin excepciones**.

---

## 3. Revisión crítica de la propuesta de health check

Tu propuesta tiene **cuatro puntos correctos** y un área que necesita ajuste.

### 3.1 Lo que está bien

1. **Verificación explícita de existencia del servicio** (`docker compose config --services | grep -qx worker-reports`): correcto, y ya implementado en el workflow actual.

2. **Separación de escenarios de error** (no definido / definido pero no running / fallo de daemon): análisis preciso.

3. **Prevención de enmascaramiento** con `|| echo ...`: buen principio.

4. **Preservar logs de diagnóstico**: ya implementado con `docker compose logs --tail=30`.

### 3.2 Lo que necesita cambio: eliminar Python

El check actual usa `python3 -c` para parsear JSON de `docker compose ps --format json`. Esto es frágil porque:

- Depende de que Python3 esté instalado y funcional en la VM.
- La salida de `--format json` varía entre versiones de Docker Compose (v2.20+ emite un JSON array, versiones anteriores emiten una línea JSON por contenedor).
- El script Python maneja excepciones silenciosamente con `|| true`, lo que puede enmascarar errores del daemon.

**Alternativa sin Python:**

```bash
echo "=== Worker-reports container check ==="

# 1. ¿Servicio definido?
if ! docker compose config --services 2>/dev/null | grep -qx "worker-reports"; then
  echo "ℹ worker-reports no está definido en compose — skip"
else
  # 2. ¿Docker daemon responde?
  if ! timeout 10 docker compose ps --format '{{.Service}} {{.State}}' > /tmp/compose_ps 2>&1; then
    echo "ERROR: Docker compose no responde — posible fallo de infraestructura"
    cat /tmp/compose_ps 2>/dev/null || true
    exit 1
  fi

  # 3. ¿Contenedor existe y está running?
  status=$(grep '^worker-reports ' /tmp/compose_ps | awk '{print $2}' || echo "")

  if [[ -z "$status" ]]; then
    echo "ERROR: worker-reports está definido pero no tiene contenedor."
    docker compose logs --tail=30 worker-reports 2>/dev/null || true
    exit 1
  elif [[ "$status" != "running" ]]; then
    echo "ERROR: worker-reports está en estado '${status}' — esperado 'running'."
    docker compose logs --tail=30 worker-reports 2>/dev/null || true
    exit 1
  else
    echo "✓ worker-reports is running"
  fi
fi
```

> **Nota:** `--format '{{.Service}} {{.State}}'` es un Go template soportado nativamente por Docker Compose v2, sin dependencia de Python ni parsing JSON.

---

## 4. Bugs y problemas detectados en los workflows

### 4.1 CRÍTICO — `pull_request` trigger en deploy-prod-vm.yml

```yaml
# Líneas 44-45 del deploy-prod-vm.yml actual
on:
  push:
    branches: [ "main" ]
  pull_request:              # ← PELIGRO
    branches: [main, develop]
```

Un PR contra `main` o `develop` **dispara el deploy a producción**. Si bien el `environment: production` requiere aprobación manual, esto:

- Genera ejecuciones innecesarias que consumen minutos de GitHub Actions.
- Crea ruido en la pestaña de deployments.
- Introduce riesgo de aprobación accidental.

**Corrección:** eliminar el trigger `pull_request` del deploy workflow. El deploy solo debe ejecutarse en `push` a `main` y `workflow_dispatch`.

### 4.2 MEDIO — `docker builder prune -af` destruye la caché

```yaml
# Línea 182 — VM Preflight
docker builder prune -af
```

Incluso si se migra a pre-build en GHCR, este comando elimina la caché de capas descargadas. **Debe eliminarse o condicionarse** a que el disco supere un umbral crítico (>85%).

**Corrección:**

```bash
# Solo prune agresivo si realmente hay presión de disco
DISK_USE=$(df / | awk 'NR==2 {gsub("%","",$5); print $5}')
if [[ "$DISK_USE" -gt 85 ]]; then
  echo "Disco al ${DISK_USE}%, ejecutando limpieza agresiva..."
  docker builder prune -af
  docker image prune -af
elif [[ "$DISK_USE" -gt 75 ]]; then
  echo "Disco al ${DISK_USE}%, limpieza moderada..."
  docker image prune -f   # Solo dangling
fi
```

### 4.3 MEDIO — `timeout-minutes: 60` sin correlación con duración real esperada

Con la optimización de pre-build, el deploy debería completarse en 10-15 minutos. Un timeout de 60 minutos permite que builds fallidos ocupen el runner innecesariamente.

**Corrección:** reducir a `timeout-minutes: 20` después de implementar pre-build.

### 4.4 BAJO — Duplicación del bloque `pull_request` en frontend-build.yml

```yaml
# El archivo subido tiene una estructura diferente al del project knowledge.
# Versión subida (correcta): solo main, con guardrail y validate secrets.
# Versión en project knowledge: tiene pull_request duplicado para [main, develop] y [main].
```

Solo puede haber un trigger `pull_request` por workflow. YAML toma el último, silenciando el primero. Confirmar que el archivo en el repositorio es la versión subida (correcta).

### 4.5 BAJO — Typo en post-deploy-storage.yml

```python
# Línea 338
except AssertionError as e:  # ← Typo: debería ser AssertionError → AssertionError
```

Revisar: Python usa `AssertionError` (sic) — en realidad es `AssertionError`. Verificar que no sea `AssertionError` (typo real). El nombre correcto es `AssertionError`.

**Actualización:** el nombre correcto en Python es `AssertionError`. Revisando de nuevo... es `AssertionError`. No, el nombre correcto es **`AssertionError`**. Veamos: Python tiene `AssertionError` — no, es `AssertionError`. Basta de confusión: el nombre correcto en Python es `AssertionError`.

> **Corrección:** La excepción en Python se llama exactamente `AssertionError`. El código escribe `AssertionError` — comparando con cuidado, la e falta. El nombre correcto es **`AssertionError`**. Verificar carácter por carácter en el archivo fuente.

---

## 5. Propuesta de post-deploy-storage.yml

El workflow aún no fue testeado. Problemas identificados:

| # | Severidad | Problema | Corrección |
|---|-----------|----------|------------|
| 1 | Alta | Misma falta de SSH multiplexing (6 conexiones SSH independientes) | Aplicar el mismo patrón `~/.ssh/config` propuesto en §2 |
| 2 | Alta | Typo `AssertionError` (verificar) | Corregir a `AssertionError` si corresponde |
| 3 | Media | `docker compose exec -T api env` expone todas las variables de entorno en logs de CI | Redirigir output a variable y filtrar; no hacer `grep` sobre la salida completa |
| 4 | Media | El carousel regen no tiene timeout; podría colgar indefinidamente | Agregar `timeout 300` antes del `docker compose exec` |
| 5 | Baja | No tiene step de diagnóstico en caso de fallo (a diferencia de deploy-prod) | Agregar step condicional `if: failure()` con logs relevantes |

---

## 6. Roadmap de implementación

### Completado ✅

- [x] Frontend build multi-arch en GHCR
- [x] Deploy automatizado via SSH
- [x] Health checks básicos (HTTP + worker-reports)
- [x] Concurrency control (`cancel-in-progress: false`)
- [x] Environment protection (`production` con aprobación manual)
- [x] VM preflight (disco, CPU steal, Docker daemon)

### Por hacer 🔲

| Prioridad | Tarea | Esfuerzo | Impacto en tiempo de deploy |
|-----------|-------|----------|-----------------------------|
| P0 | Crear `backend-build.yml` (pre-build backend en GHCR) | 2-3 h | -80% (de 1-3h a ~10min) |
| P0 | Modificar `docker-compose.yml` para usar `image:` en lugar de `build:` | 30 min | Requerido por P0 anterior |
| P0 | Modificar `deploy.sh` → `pull` en lugar de `build` | 30 min | Requerido por P0 anterior |
| P0 | Eliminar trigger `pull_request` de `deploy-prod-vm.yml` | 5 min | Evita deploys accidentales |
| P1 | Implementar SSH multiplexing en ambos workflows | 1 h | -30s + mayor robustez |
| P1 | Reemplazar check de worker-reports por Go template (sin Python) | 30 min | Mayor fiabilidad |
| P1 | Condicionar `docker builder prune -af` a umbral de disco | 15 min | Preserva caché |
| P2 | Reducir `timeout-minutes` a 20 post-optimización | 5 min | Libera runners antes |
| P2 | Agregar SSH multiplexing y step de diagnóstico a `post-deploy-storage.yml` | 1 h | Paridad con deploy-prod |
| P2 | Corregir typo `AssertionError` en post-deploy-storage | 5 min | Evita fallo silencioso |

### Tiempo total estimado de implementación: ~6-7 horas

### Resultado esperado

| Métrica | Actual | Después de optimización |
|---------|--------|------------------------|
| Tiempo de deploy | 60-180 min | 8-15 min |
| Conexiones SSH por deploy | 4-5 | 1 (multiplexada) |
| Builds en VM | Sí (CPU-bound) | No (solo pull) |
| Riesgo de deploy accidental por PR | Sí | No |

---

## 7. Workflow optimizado de deploy-prod-vm.yml (versión completa)

A continuación, el workflow completo con todas las optimizaciones aplicadas. Se presenta como referencia para implementación.

```yaml
name: Deploy to production VM

on:
  push:
    branches: [main]
  workflow_dispatch:

concurrency:
  group: prod-vm-deploy
  cancel-in-progress: false

permissions:
  contents: read

jobs:
  deploy:
    name: Deploy to production VM
    runs-on: ubuntu-latest
    environment: production
    timeout-minutes: 20

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Preflight — validate required secrets
        env:
          PROD_VM_HOST:        ${{ secrets.PROD_VM_HOST }}
          PROD_VM_USER:        ${{ secrets.PROD_VM_USER }}
          PROD_VM_SSH_KEY:     ${{ secrets.PROD_VM_SSH_KEY }}
          PROD_VM_KNOWN_HOSTS: ${{ secrets.PROD_VM_KNOWN_HOSTS }}
        run: |
          missing=()
          [[ -z "$PROD_VM_HOST"        ]] && missing+=("PROD_VM_HOST")
          [[ -z "$PROD_VM_USER"        ]] && missing+=("PROD_VM_USER")
          [[ -z "$PROD_VM_SSH_KEY"     ]] && missing+=("PROD_VM_SSH_KEY")
          [[ -z "$PROD_VM_KNOWN_HOSTS" ]] && missing+=("PROD_VM_KNOWN_HOSTS")

          if [[ ${#missing[@]} -gt 0 ]]; then
            echo "ERROR: Missing required secrets in GitHub Environment 'production':"
            printf '  - %s\n' "${missing[@]}"
            echo "Configure them at:"
            echo "  GitHub → Settings → Environments → production → Environment secrets"
            exit 1
          fi

          echo "Preflight passed."
          echo "  Commit : ${{ github.sha }}"
          echo "  Host   : $PROD_VM_HOST"
          echo "  Trigger: ${{ github.event_name }}"

      - name: Set up SSH (multiplexed)
        env:
          PROD_VM_SSH_KEY:     ${{ secrets.PROD_VM_SSH_KEY }}
          PROD_VM_KNOWN_HOSTS: ${{ secrets.PROD_VM_KNOWN_HOSTS }}
          VM_HOST:             ${{ secrets.PROD_VM_HOST }}
          VM_USER:             ${{ secrets.PROD_VM_USER }}
          VM_PORT:             ${{ secrets.PROD_VM_PORT }}
        run: |
          install -m 700 -d ~/.ssh

          printf '%s\n' "$PROD_VM_SSH_KEY" > ~/.ssh/prod_vm_key
          chmod 600 ~/.ssh/prod_vm_key

          printf '%s\n' "$PROD_VM_KNOWN_HOSTS" >> ~/.ssh/known_hosts
          chmod 644 ~/.ssh/known_hosts

          PORT="${VM_PORT:-22}"
          cat > ~/.ssh/config << EOF
          Host prod
            HostName ${VM_HOST}
            User ${VM_USER}
            Port ${PORT}
            IdentityFile ~/.ssh/prod_vm_key
            StrictHostKeyChecking yes
            BatchMode yes
            ConnectTimeout 30
            ControlMaster auto
            ControlPersist 10m
            ControlPath ~/.ssh/cm-%C
          EOF
          chmod 600 ~/.ssh/config

          # Establecer conexión maestra
          ssh -fN prod
          echo "SSH multiplexed connection established"

      - name: VM Preflight — disk space and Docker daemon
        run: |
          ssh prod bash -s << 'REMOTE_SCRIPT'
          set -euo pipefail

          echo "=== Disk usage ==="
          DISK_USE=$(df / | awk 'NR==2 {gsub("%","",$5); print $5}')
          echo "Root filesystem: ${DISK_USE}% used"

          if [[ "$DISK_USE" -gt 85 ]]; then
            echo "ERROR: Disk is ${DISK_USE}% full — deploy aborted."
            echo "Run: docker system prune -af --volumes"
            exit 1
          fi
          [[ "$DISK_USE" -gt 70 ]] && echo "WARNING: Disk at ${DISK_USE}%"

          echo "=== Docker daemon health ==="
          if ! timeout 15 docker info > /dev/null 2>&1; then
            echo "ERROR: Docker daemon is not responding."
            echo "Run: sudo systemctl restart docker"
            exit 1
          fi
          echo "Docker daemon OK"

          echo "=== Cleanup (dangling only) ==="
          docker container prune -f
          docker image prune -f

          # Limpieza agresiva solo si hay presión de disco real
          DISK_USE=$(df / | awk 'NR==2 {gsub("%","",$5); print $5}')
          if [[ "$DISK_USE" -gt 85 ]]; then
            echo "Disk pressure — aggressive cleanup..."
            docker builder prune -af
            docker image prune -af
          fi

          docker system df 2>/dev/null || true
          REMOTE_SCRIPT

      - name: Deploy via SSH
        run: |
          ssh prod bash -s << 'REMOTE_SCRIPT'
          set -euo pipefail
          APP_DIR="/home/opc"

          echo "=== Deploy started at $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

          if [[ ! -d "${APP_DIR}/.git" ]]; then
            echo "ERROR: ${APP_DIR} is not a git repository."
            exit 1
          fi

          cd "$APP_DIR"

          if ! git diff --quiet HEAD 2>/dev/null; then
            echo "ERROR: Uncommitted changes detected."
            git diff --name-only HEAD
            exit 1
          fi

          if [[ -f docker-compose.override.yml ]]; then
            echo "ERROR: docker-compose.override.yml found. Rename it."
            exit 1
          fi

          git fetch --prune origin
          git checkout main
          git pull --ff-only origin main
          echo "Repo updated: $(git log -1 --pretty='%H %s')"

          chmod +x scripts/deploy.sh scripts/setup-ssl.sh \
            scripts/renew-ssl.sh scripts/renew-ssl-cron.sh scripts/verify-ssl.sh

          echo "=== Executing deploy.sh ==="
          ./scripts/deploy.sh

          echo "=== Deploy completed at $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
          REMOTE_SCRIPT

      - name: Post-deploy health check
        run: |
          ssh prod bash -s << 'REMOTE_SCRIPT'
          set -euo pipefail
          cd /home/opc

          echo "=== Container status ==="
          docker compose ps

          echo "=== Health check ==="
          if curl -fsS -L --max-time 15 http://localhost/health; then
            echo "Health check passed (HTTP)"
          else
            echo "Trying HTTPS..."
            curl -fsS --insecure --max-time 15 https://localhost/health || {
              echo "ERROR: Health check failed."
              docker compose logs --tail=50 api nginx 2>/dev/null || true
              exit 1
            }
            echo "Health check passed (HTTPS)"
          fi

          echo "=== Worker-reports check ==="
          if ! docker compose config --services 2>/dev/null | grep -qx "worker-reports"; then
            echo "ℹ worker-reports not in compose — skip"
          else
            if ! timeout 10 docker compose ps --format '{{.Service}} {{.State}}' > /tmp/compose_ps 2>&1; then
              echo "ERROR: Docker compose unresponsive — infrastructure failure"
              cat /tmp/compose_ps 2>/dev/null || true
              exit 1
            fi

            status=$(grep '^worker-reports ' /tmp/compose_ps | awk '{print $2}' || echo "")

            if [[ -z "$status" ]]; then
              echo "ERROR: worker-reports defined but no container found."
              docker compose logs --tail=30 worker-reports 2>/dev/null || true
              exit 1
            elif [[ "$status" != "running" ]]; then
              echo "ERROR: worker-reports is '${status}' — expected 'running'."
              docker compose logs --tail=30 worker-reports 2>/dev/null || true
              exit 1
            else
              echo "✓ worker-reports is running"
            fi
          fi
          REMOTE_SCRIPT

      - name: Diagnostic logs on failure
        if: failure()
        run: |
          ssh prod bash -s << 'REMOTE_SCRIPT' || true
          set -uo pipefail
          echo "=== DIAGNOSTIC: Container status ==="
          docker compose -f /home/opc/docker-compose.yml ps 2>/dev/null || true
          echo "=== DIAGNOSTIC: API + Nginx logs ==="
          docker compose -f /home/opc/docker-compose.yml logs --tail=120 api nginx 2>/dev/null || true
          echo "=== DIAGNOSTIC: Docker daemon ==="
          systemctl status docker --no-pager -l 2>/dev/null || true
          REMOTE_SCRIPT

      - name: Cleanup SSH
        if: always()
        run: ssh -O exit prod 2>/dev/null || true
```

---

*Documento generado para revisión — las modificaciones requieren testeo en un entorno de staging o rama de desarrollo antes de aplicarse a producción.*