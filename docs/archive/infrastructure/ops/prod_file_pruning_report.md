# ForestGuard — Production File Pruning Report

> **Fecha**: 2026-02-16  
> **Objetivo**: Minimizar el tamaño del deploy a la VM (Oracle Cloud) identificando archivos innecesarios para producción.

---

## 1. Resumen Ejecutivo

| Métrica | Valor |
|---|---|
| Tamaño estimado del repo completo | ~2.0 GB |
| **Ahorro conservador** | **~1.75 GB (87%)** |
| **Ahorro agresivo** | **~1.87 GB (93%)** |
| **Bundle de producción estimado** | **~130–260 MB** (antes de instalar venv en VM) |

### Qué excluir YA (impacto inmediato)

| Directorio | Tamaño | Riesgo de excluir |
|---|---|---|
| `.venv/` | 639 MB | Ninguno — se recrea con `pip install` |
| `venv/` | 506 MB | Ninguno — se recrea con `pip install` |
| `frontend/node_modules/` | 345 MB | Ninguno — solo si frontend se buildea en otro lado |
| `data/raw/` | 180 MB | Ninguno — datos históricos de FIRMS/áreas protegidas |
| `.git/` | 87 MB | Ninguno si usás `rsync`/`tar` en vez de `git clone` |
| `.mypy_cache/` | 65 MB | Ninguno — cache de type checking |
| `temp_files/` | 61 MB | Ninguno — logs locales dev + scripts temporales |
| `tests/` | 35 MB | Ninguno — no se corren en producción |
| `logs/` | 19 MB | Ninguno — logs locales, la VM genera los suyos |
| `node_modules/` (root) | 18 MB | Ninguno — no hay runtime Node en backend |
| `htmlcov/` | 7 MB | Ninguno — reportes de coverage |
| `docs/` | 6 MB | Ninguno — documentación, no usada en runtime |

**Total excluible: ~1.97 GB → Bundle de deploy: ~130 MB** (sin contar el venv que se instala en la VM).

---

## 2. Runtime Mínimo Detectado

### Arquitectura de producción (actual)

```
Oracle Cloud VM (Oracle Linux)
├── systemd: forestguard.service
│   └── gunicorn + uvicorn workers (app/main.py)
├── systemd: nginx
│   └── Reverse proxy + SSL (Let's Encrypt)
├── systemd: redis-server
│   └── Celery broker + result backend
├── Celery workers (ingestion, clustering, analysis)
├── Celery beat (scheduler)
└── DB: Supabase (remoto, no corre en VM)
```

> **Frontend**: NO corre en la VM. Se puede hostear en CDN/Vercel/Netlify o servir el `dist/` como archivos estáticos desde nginx (solo 1.1 MB el build).

### Árbol mínimo requerido en VM

```
/opt/forestguard/                     # WorkingDirectory del systemd service
├── .env                              # ✅ Variables de entorno (se crea en la VM, no se copia)
├── requirements.txt                  # ✅ Para instalar dependencias
├── pyproject.toml                    # ✅ Config de proyecto Python
├── celery_app.py                     # ✅ Entry point de Celery (root)
├── app/                              # ✅ FastAPI application (~8 MB)
│   ├── main.py
│   ├── api/
│   ├── core/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   └── utils/
├── workers/                          # ✅ Celery workers (~0.12 MB)
│   ├── __init__.py
│   ├── celery_app.py
│   └── tasks/
├── database/                         # ✅ Alembic migrations (~0.19 MB)
│   ├── alembic.ini
│   ├── env.py
│   └── versions/
├── deployment/                       # 🟡 Configs de referencia (~0.01 MB)
│   ├── forestguard.service
│   └── nginx.conf
└── venv/                             # ✅ Se crea in-situ con pip install
```

### Componentes fuera de la VM

| Componente | Dónde corre | Acción |
|---|---|---|
| Frontend (React/Vite) | CDN / Vercel / VM-nginx static | No copiar `frontend/src/`, `node_modules/`. Solo copiar `frontend/dist/` si se sirve desde la VM |
| Base de datos (PostgreSQL+PostGIS) | Supabase (remoto) | Solo se necesita connectividad, no archivos locales |
| GCS Storage | Google Cloud | Buckets remotos, no storage local |
| Docker Compose | Solo desarrollo local | No se usa en producción |

---

## 3. Top 50 Rutas por Tamaño

### Directorios (ordenado por tamaño descendente)

| # | Ruta | Tamaño | Tipo | En prod? |
|---|---|---|---|---|
| 1 | `.venv/` | 639 MB | Dependencias Python | ❌ |
| 2 | `venv/` | 506 MB | Dependencias Python (duplicado) | ❌ |
| 3 | `frontend/node_modules/` | 345 MB | Dependencias Node.js | ❌ |
| 4 | `data/raw/` | 180 MB | Datos FIRMS + áreas protegidas | ❌ |
| 5 | `.git/` | 87 MB | Historial Git | ❌ |
| 6 | `.mypy_cache/` | 65 MB | Cache mypy | ❌ |
| 7 | `temp_files/` | 61 MB | Logs dev + scripts temp | ❌ |
| 8 | `tests/` | 35 MB | Tests unitarios/integración/e2e | ❌ |
| 9 | `logs/` | 19 MB | Logs locales | ❌ |
| 10 | `node_modules/` (root) | 18 MB | Dependencias Node.js (root) | ❌ |
| 11 | `app/` | 8 MB | Aplicación FastAPI | ✅ |
| 12 | `htmlcov/` | 7 MB | Coverage HTML | ❌ |
| 13 | `docs/` | 6 MB | Documentación | ❌ |
| 14 | `frontend/dist/` | 1.1 MB | Build de producción | 🟡 |
| 15 | `frontend/playwright-report/` | 0.77 MB | Reportes Playwright | ❌ |
| 16 | `scripts/` | 0.38 MB | Scripts operacionales | 🟡 |
| 17 | `frontend/test-results/` | 0.26 MB | Resultados de tests | ❌ |
| 18 | `database/` | 0.19 MB | Alembic migrations | ✅ |
| 19 | `workers/` | 0.12 MB | Celery workers | ✅ |
| 20 | `deployment/` | 0.01 MB | Configs de deploy | 🟡 |
| 21 | `docker/` | 0.02 MB | Docker compose (dev) | ❌ |
| 22 | `.github/` | 0.01 MB | CI/CD workflows | ❌ |
| 23 | `supabase/` | 0.01 MB | Supabase config | ❌ |
| 24 | `changes/` | 0.02 MB | Changelogs | ❌ |
| 25 | `secrets/` | ~0.004 MB | **⚠️ Credenciales** | **Ver §6** |

### Archivos individuales pesados

| # | Archivo | Tamaño | En prod? |
|---|---|---|---|
| 1 | `temp_files/uvicorn.venv.err.log` | 61 MB | ❌ |
| 2 | `logs/wildfire_api.log` | 19 MB | ❌ |
| 3 | `frontend/package-lock.json` | 0.38 MB | ❌ |
| 4 | `tests/flake8_log.txt` | 0.17 MB | ❌ |
| 5 | `.coverage` | 0.07 MB | ❌ |
| 6 | `celerybeat-schedule` | 0.002 MB | ❌ |
| 7 | `.env.bak` | 0.006 MB | ❌ |

---

## 4. Clasificación Detallada por "Necesario en Producción"

### ✅ Requerido en producción (NO tocar)

| Ruta | Justificación |
|---|---|
| `app/` | Aplicación FastAPI completa: API, servicios, modelos, config |
| `workers/` | Workers de Celery (ingestion, clustering, analysis) |
| `celery_app.py` | Entry point de Celery desde root |
| `requirements.txt` | Necesario para instalar dependencias en la VM |
| `pyproject.toml` | Configuración del proyecto Python |
| `database/` | Migraciones Alembic (necesarias para schema updates) |
| `.env` | Variables de entorno — **pero NO copiar: crear en la VM** |

### 🟡 Opcional (solo si habilitás feature X)

| Ruta | Condición | Justificación |
|---|---|---|
| `frontend/dist/` | Solo si servís frontend desde la VM nginx | Si usás CDN/Vercel, no hace falta |
| `deployment/` | Solo referencia para setup inicial | Contiene `forestguard.service` y `nginx.conf` de referencia |
| `scripts/` | Solo algunos scripts operacionales | `deploy.sh`, `load_firms_*.py`, `aggregate_*.py` pueden ser útiles para ops manuales |
| `scripts/load_firms_history.py` | Re-ingesta retroactiva de FIRMS | Solo si se necesita cargar datos desde cero |
| `scripts/load_protected_areas.py` | Carga inicial de áreas protegidas | Solo en setup inicial o actualización de shapes |
| `scripts/aggregate_fire_episodes.py` | Regeneración de episodios | Solo para mantenimiento manual |

### ❌ Innecesario en producción (seguro excluir del deploy)

| Ruta | Tamaño | Justificación |
|---|---|---|
| `.venv/` | 639 MB | Se recrea con `pip install -r requirements.txt` en la VM |
| `venv/` | 506 MB | Ídem (duplicado del anterior) |
| `frontend/node_modules/` | 345 MB | Dependencias de build del frontend, no se usan en VM |
| `frontend/src/` | ~3 MB | Código fuente del frontend, no se ejecuta en VM |
| `data/` | 180 MB | Datos brutos de FIRMS/áreas protegidas (ya cargados en Supabase) |
| `.git/` | 87 MB | Historial Git (no se necesita en VM si usás rsync/tar) |
| `.mypy_cache/` | 65 MB | Cache del type checker |
| `temp_files/` | 61 MB | Logs de desarrollo y archivos temporales |
| `tests/` | 35 MB | Suites de tests (unit/integration/e2e) |
| `logs/` | 19 MB | Logs de desarrollo local |
| `node_modules/` (root) | 18 MB | No hay runtime Node.js en el backend |
| `htmlcov/` | 7 MB | Reportes de coverage HTML |
| `docs/` | 6 MB | Documentación técnica |
| `.pytest_cache/` | 0.03 MB | Cache de pytest |
| `__pycache__/` | ~0 MB | Cache de Python (se regenera) |
| `.github/` | 0.01 MB | Workflows de CI/CD |
| `docker/` | 0.02 MB | Docker Compose de desarrollo |
| `docker-compose.yml` (root) | 0.006 MB | Docker Compose de desarrollo |
| `Dockerfile.api` | 0.0007 MB | No se usa Docker en prod VM |
| `Dockerfile.worker` | 0.0008 MB | Ídem |
| `frontend/Dockerfile` | 0.0007 MB | Ídem |
| `frontend/cypress/` | 0.01 MB | Tests E2E de Cypress |
| `frontend/tests/` | 0.02 MB | Tests del frontend |
| `frontend/test-results/` | 0.26 MB | Resultados de Playwright |
| `frontend/playwright-report/` | 0.77 MB | Reportes de Playwright |
| `supabase/` | 0.01 MB | Config de Supabase |
| `changes/` | 0.02 MB | Changelogs |
| `.coverage` | 0.07 MB | Archivo de coverage |
| `celerybeat-schedule` | 0.002 MB | Schedule local de celery-beat |
| `.env.bak` | 0.006 MB | Backup de .env |
| `.env.template` | 0.007 MB | Template (referencia solamente) |
| `check_*.py` (root) | ~0.01 MB | Scripts de debug sueltos en root |
| `debug_*.py` (root) | ~0.002 MB | Scripts de debug sueltos en root |
| `reproduce_issue.py` | 0.001 MB | Script de debug |
| `README.md` | 0.02 MB | No se necesita en runtime |
| `pytest.ini` | 0.0002 MB | Config de pytest |
| `*.log` (todos) | ~19 MB | Logs antiguos |

---

## 5. Plantillas de Exclusión

### 5.1 rsync `--exclude` patterns

#### CONSERVADORA (riesgo mínimo — excluye ~1.75 GB)

```bash
# Archivo: deploy_excludes_conservative.txt
# Virtual environments
.venv/
venv/

# Node.js
node_modules/

# Git history
.git/
.gitattributes

# Caches
.mypy_cache/
.pytest_cache/
__pycache__/
htmlcov/
.coverage
.coverage.*

# Logs y temporales
logs/
temp_files/
*.log
celerybeat-schedule

# Tests
tests/
pytest.ini
frontend/cypress/
frontend/tests/
frontend/test-results/
frontend/playwright-report/
frontend/playwright.config.ts
frontend/cypress.config.ts

# Data (ya cargados en Supabase)
data/

# Documentación
docs/

# Docker (no se usa en prod VM)
docker/
docker-compose.yml
Dockerfile.*
frontend/Dockerfile

# CI/CD
.github/

# IDEs y OS
.vscode/
.idea/
.DS_Store
Thumbs.db

# Archivos de debug root
debug_*.py
check_*.py
reproduce_issue.py

# Env backups
.env.bak
.env.template

# Misc
changes/
supabase/
README.md
```

#### AGRESIVA (máxima reducción — excluye ~1.87 GB)

```bash
# Archivo: deploy_excludes_aggressive.txt
# Incluye todo lo conservador +

# Frontend completo (si se hostea en CDN/Vercel)
frontend/

# Scripts (si no se necesitan ops manuales)
scripts/

# Deployment configs (ya configurados en la VM)
deployment/

# Archivos root innecesarios
pyproject.toml
.gitignore

# ⚠️ RIESGOS de la variante agresiva:
# - Sin frontend/: necesitás un pipeline separado para servir el frontend
# - Sin scripts/: perdés la capacidad de hacer ops manuales desde la VM
#   (p.ej. load_firms_history.py, aggregate_fire_episodes.py)
# - Sin deployment/: si necesitás reconfigurar nginx o systemd,
#   deberás bajar los archivos individualmente
```

### 5.2 `.dockerignore` (para builds Docker, si se vuelve a usar)

```dockerignore
# === .dockerignore ===
# Virtual environments
.venv
venv

# Node.js
node_modules

# Git
.git
.gitattributes
.gitignore

# Caches
.mypy_cache
.pytest_cache
__pycache__
htmlcov
.coverage
.coverage.*

# Logs y temporales
logs
temp_files
*.log

# Tests
tests
pytest.ini

# Data
data

# Docs
docs
changes
README.md

# Frontend (el API no necesita el frontend)
frontend

# Docker (evitar recursión)
docker
docker-compose.yml
Dockerfile.*

# CI/CD
.github

# IDE y OS
.vscode
.idea
.DS_Store
Thumbs.db

# Debug scripts
debug_*.py
check_*.py
reproduce_issue.py

# Env files (se pasan como variables de entorno)
.env
.env.*

# Secrets (NUNCA incluir en imagen Docker)
secrets
```

### 5.3 `.gitignore` (adiciones recomendadas)

El `.gitignore` actual ya es bastante bueno. Adiciones sugeridas:

```gitignore
# Ya existentes y correctos (verificados):
# .venv/, venv/, node_modules/, logs/, data/, temp_files/, htmlcov/,
# .coverage, .pytest_cache/, __pycache__/, .mypy_cache/ (FALTA)

# Agregar:
.mypy_cache/
.ruff_cache/
celerybeat-schedule
*.pyc
```

---

## 6. Hallazgos de Seguridad

> [!CAUTION]
> **Credenciales encontradas en el repositorio**

| Archivo | Tipo | Acción recomendada |
|---|---|---|
| `secrets/gee-service-account.json` | Service Account Key de Google Earth Engine | ⚠️ **NO copiar a la VM por rsync.** Ya debería estar en `/opt/secrets/` en la VM. Añadir a `.dockerignore` y exclusions de rsync. |
| `secrets/clientLibraryConfig-oracle-free-tier.json` | Configuración Oracle Cloud | ⚠️ Ídem. No copiar. |
| `.env` | Variables de entorno con passwords | **NUNCA copiar.** Crear manualmente en la VM con `nano /opt/forestguard/.env` |
| `.env.bak` | Backup de .env | **Eliminar del repo.** |
| `docker/docker-compose.yml` línea 60 | `GCS_PROJECT_ID` hardcodeado | Mover a variable de entorno |

### Estrategia para `secrets/`

1. El directorio `secrets/` ya está en `.gitignore` ✅
2. **Debe estar en las exclusiones de rsync/tar** ✅ (incluido arriba)
3. En la VM, las credenciales van en `/opt/secrets/` con `chmod 600`
4. Nunca incluir en imágenes Docker

### Estrategia para storage local (`STORAGE_BACKEND=local`)

El código ya bloquea `STORAGE_BACKEND=local` en producción (ver `app/core/config.py:172-179` y `app/services/storage_service.py:151-156`). En producción se usa GCS. No hay datos de storage local que migrar ya que todo va a buckets de GCS.

---

## 7. Plan de "Release Bundle" Recomendado

### Opción A: rsync directo (recomendada)

```bash
# === Desde tu máquina local ===

# 1. Generar bundle limpio con rsync
rsync -avz --progress \
  --exclude-from=deploy_excludes_conservative.txt \
  --exclude=secrets/ \
  --exclude=.env \
  --exclude=.env.bak \
  /path/to/wildfire-recovery-argentina/ \
  opc@<VM_IP>:/opt/forestguard/

# 2. En la VM: instalar dependencias
ssh opc@<VM_IP> << 'EOF'
cd /opt/forestguard
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
sudo systemctl restart forestguard
EOF
```

### Opción B: tar.gz release bundle

```bash
# === Desde tu máquina local ===

# 1. Crear tarball excluyendo lo innecesario
tar czf forestguard-release-$(date +%Y%m%d).tar.gz \
  --exclude='.venv' \
  --exclude='venv' \
  --exclude='node_modules' \
  --exclude='.git' \
  --exclude='.mypy_cache' \
  --exclude='.pytest_cache' \
  --exclude='__pycache__' \
  --exclude='htmlcov' \
  --exclude='logs' \
  --exclude='temp_files' \
  --exclude='data' \
  --exclude='tests' \
  --exclude='docs' \
  --exclude='docker' \
  --exclude='frontend/node_modules' \
  --exclude='frontend/test-results' \
  --exclude='frontend/playwright-report' \
  --exclude='frontend/cypress' \
  --exclude='frontend/tests' \
  --exclude='.github' \
  --exclude='changes' \
  --exclude='supabase' \
  --exclude='secrets' \
  --exclude='.env' \
  --exclude='.env.bak' \
  --exclude='.coverage' \
  --exclude='*.log' \
  --exclude='celerybeat-schedule' \
  --exclude='debug_*.py' \
  --exclude='check_*.py' \
  --exclude='reproduce_issue.py' \
  -C /path/to/ wildfire-recovery-argentina/

# 2. Copiar a la VM
scp forestguard-release-*.tar.gz opc@<VM_IP>:/tmp/

# 3. En la VM: desplegar
ssh opc@<VM_IP> << 'EOF'
cd /opt/forestguard
tar xzf /tmp/forestguard-release-*.tar.gz --strip-components=1
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart forestguard
rm /tmp/forestguard-release-*.tar.gz
EOF
```

### Opción C: git sparse-checkout (para actualizaciones incrementales)

```bash
# === En la VM ===

# Setup inicial (una vez)
cd /opt/forestguard
git init
git remote add origin https://github.com/Nicolasgh91/wildfire-recovery-argentina.git
git sparse-checkout init --cone
git sparse-checkout set app workers database deployment scripts celery_app.py requirements.txt pyproject.toml

# Pull solo lo necesario
git pull origin main

# Crear venv e instalar deps
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Actualización posterior
git pull origin main
pip install -r requirements.txt
sudo systemctl restart forestguard
```

---

## 8. Comandos de Auditoría para la VM

### Medir tamaños actuales

```bash
# Top 20 directorios más pesados
du -sh /opt/forestguard/*/ 2>/dev/null | sort -rh | head -20

# Tamaño total del deploy
du -sh /opt/forestguard/

# Archivos más grandes (top 20)
find /opt/forestguard -type f -exec du -sh {} + 2>/dev/null | sort -rh | head -20
```

### Encontrar basura típica

```bash
# Caches de Python
find /opt/forestguard -type d -name '__pycache__' -o -name '.pytest_cache' -o -name '.mypy_cache'

# Logs viejos
find /opt/forestguard -name '*.log' -mtime +7 -ls

# Archivos temporales
find /opt/forestguard -name '*.tmp' -o -name '*.bak' -o -name '*.swp'

# Node modules que no deberian estar
find /opt/forestguard -type d -name 'node_modules'

# Venvs duplicados
find /opt/forestguard -type d -name '.venv' -o -name 'venv' | head -5
```

### Limpiar con cuidado

```bash
# Limpiar __pycache__ (seguro, se regenera)
find /opt/forestguard -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null

# Limpiar logs > 7 días (conservador)
find /opt/forestguard -name '*.log' -mtime +7 -delete

# Limpiar pip cache (después de instalar deps)
pip cache purge

# Verificar espacio libre
df -h /opt/forestguard
```

---

## 9. Riesgos y Verificación Post-Deploy (Checklist)

### Pre-deploy (en tu máquina local)

- [ ] Verificar que `requirements.txt` está actualizado con las dependencias correctas
- [ ] Verificar que `database/` tiene todas las migraciones Alembic pendientes
- [ ] Confirmar que `workers/celery_app.py` importa todas las queues necesarias
- [ ] NO incluir `.env`, `secrets/`, credenciales en el bundle

### Post-deploy (en la VM)

- [ ] `source venv/bin/activate && python -c "import app; print('OK')"` — verifica imports
- [ ] `curl http://localhost:8000/health` — API responde health check
- [ ] `sudo systemctl status forestguard` — servicio activo sin errores
- [ ] `celery -A workers.celery_app inspect ping` — workers responden
- [ ] `redis-cli ping` — Redis funciona
- [ ] `alembic -c database/alembic.ini current` — migraciones al día
- [ ] `curl https://forestguard.freedynamicdns.org/health` — HTTPS funciona end-to-end
- [ ] Verificar logs: `sudo journalctl -u forestguard -n 50 --no-pager`

### Riesgos identificados

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Falta una dependencia Python que no está en `requirements.txt` | Media | Correr `pip freeze` antes de crear bundle y comparar |
| Migración Alembic faltante | Baja | Incluir siempre `database/` completo |
| Worker no encuentra módulo de `scripts/` | Baja | los workers importan de `app/` y `workers/`, no de `scripts/` |
| Frontend no disponible si se excluye `frontend/dist/` | Media | Solo excluir frontend si ya está en CDN |
| Script de ops necesario no copiado | Media | Incluir `scripts/` en variante conservadora |
| Credenciales GEE faltantes | Media | Verificar `/opt/secrets/gee-service-account.json` post-deploy |

---

## Apéndice: Resumen de Componentes Docker (solo para referencia)

Los archivos Docker **no se usan en producción** actual (la VM usa systemd directo):

| Archivo | Propósito | En producción |
|---|---|---|
| `docker-compose.yml` (root) | Stack de desarrollo simplificado | ❌ |
| `docker/docker-compose.yml` | Stack completo con nginx+certbot | ❌ (pero podría usarse en futuro) |
| `Dockerfile.api` | Build de imagen API | ❌ |
| `Dockerfile.worker` | Build de imagen worker | ❌ |
| `frontend/Dockerfile` | Build de imagen frontend (multi-stage) | ❌ |

> **Nota**: Si en el futuro se migra a Docker en producción, el `.dockerignore` propuesto en §5.2 es esencial para evitar copiar ~2 GB de archivos innecesarios dentro de la imagen Docker (actualmente los Dockerfiles hacen `COPY . .` sin ningún filtro).
