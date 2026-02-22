# Análisis de Archivos VM - ForestGuard Producción

## Resumen Ejecutivo

**Espacio Total Analizado**: ~1.5 GB  
**Espacio Optimizable**: ~1.2 GB (80%)  
**Espacio Esencial**: ~300 MB (20%)

---

## Análisis por Directorio

### 🔴 ARCHIVOS CRÍTICOS PARA PRODUCCIÓN (Mantener)

| Directorio | Tamaño | Uso | Acción |
|------------|--------|-----|--------|
| `app/` | 7.79 MB | Código API principal | **Mantener** |
| `frontend/dist/` | ~2 MB | Build producción frontend | **Mantener** |
| `deployment/` | 0.01 MB | Config systemd/nginx | **Mantener** |
| `database/` | 0.14 MB | Migraciones DB | **Mantener** |
| `workers/` | 0.12 MB | Workers Celery | **Mantener** |
| `.env` | - | Configuración producción | **Mantener** |
| `requirements.txt` | - | Dependencias Python | **Mantener** |
| `pyproject.toml` | - | Configuración proyecto | **Mantener** |
| `celery_app.py` | 3.6 KB | Configuración Celery | **Mantener** |

**Total Crítico**: ~10 MB

---

### 🟡 ARCHIVOS TEMPORALES/CACHE (Eliminar Inmediatamente)

| Directorio | Tamaño | Contenido | Ahorro |
|------------|--------|-----------|--------|
| `.venv/` | 638.98 MB | Entorno virtual local | **638.98 MB** |
| `venv/` | 506.28 MB | Entorno virtual backup | **506.28 MB** |
| `.mypy_cache/` | 65.28 MB | Cache mypy | **65.28 MB** |
| `htmlcov/` | 7.12 MB | Reportes cobertura | **7.12 MB** |
| `.pytest_cache/` | 0.03 MB | Cache pytest | **0.03 MB** |
| `__pycache__/` | ~0.01 MB | Cache Python | **0.01 MB** |

**Total Temporales**: **1,217.70 MB**

---

### 🟠 ARCHIVOS A EVALUAR (Parcialmente Eliminables)

#### `frontend/` - 349.20 MB
- **Mantener**: `dist/` (~2 MB) - Build producción
- **Eliminar**: `node_modules/` (349 MB) - Dependencias desarrollo
- **Mantener**: `package.json`, `vite.config.ts` - Configuración

**Ahorro Frontend**: ~347 MB

#### `scripts/` - 0.38 MB
**Scripts Esenciales (Mantener)**:
- `run_migration.py` - Migraciones DB
- `load_firms_incremental.py` - Datos diarios NASA
- `aggregate_fire_episodes.py` - Procesamiento episodios
- `run_carousel_local.py` - Imágenes satelitales

**Scripts Eliminables**:
- `debug_*.py`, `check_*.py` - Desarrollo
- `*_manual_run.md` - Documentación temporal
- `test_*.py` - Pruebas

**Ahorro Scripts**: ~0.2 MB

#### `logs/` - 19.29 MB
- **Mantener**: Configuración rotación logs
- **Limpiar**: Logs antiguos (>7 días)
- **Ahorro potencial**: ~15 MB

#### `temp_files/` - 61.37 MB
- **Eliminar**: Logs temporales, archivos de debug
- **Ahorro**: ~61 MB

---

### 🔵 ARCHIVOS OPCIONALES (Decisión del Usuario)

| Directorio | Tamaño | Uso | Recomendación |
|------------|--------|-----|---------------|
| `tests/` | 0.88 MB | Tests unitarios/integración | **Eliminar en producción** |
| `docs/` | 6.39 MB | Documentación técnica | **Opcional** |
| `data/` | 179.95 MB | Datos crudos (vacío) | **Investigar contenido** |
| `.github/` | 0.01 MB | Config CI/CD | **Eliminar** |
| `docker/` | 0.02 MB | Config Docker | **Eliminar si usa systemd** |
| `supabase/` | 0.01 MB | Edge functions | **Mantener si usa** |

---

## Scripts de Debug/Desarrollo (Eliminar)

| Archivo | Tamaño | Propósito |
|---------|--------|-----------|
| `debug_app_diagnostics.py` | 844 B | Debug aplicación |
| `debug_imports.py` | 786 B | Debug imports |
| `reproduce_issue.py` | 1.2 KB | Reproducir errores |
| `check_audit_events.py` | 2.0 KB | Verificación eventos |
| `check_eligible_episodes.py` | 2.6 KB | Verificación episodios |
| `check_existing_episodes.py` | 2.1 KB | Verificación existentes |

**Total Debug**: ~10 KB

---

## Plan de Limpieza Recomendado

### Fase 1: Limpieza Segura (Sin Riesgo)
```bash
# Eliminar caches y temporales
rm -rf .venv/ venv/ .mypy_cache/ htmlcov/ .pytest_cache/ __pycache__/
rm -rf temp_files/
rm debug_*.py reproduce_issue.py check_*.py

# Limpiar frontend
cd frontend
rm -rf node_modules/
```

**Ahorro Fase 1**: ~1.23 GB

### Fase 2: Limpieza Opcional
```bash
# Eliminar tests y documentación (opcional)
rm -rf tests/ docs/

# Limpiar logs antiguos
find logs/ -name "*.log" -mtime +7 -delete

# Eliminar configs no usadas
rm -rf .github/ docker/
```

**Ahorro Fase 2**: ~27 MB

### Fase 3: Optimización Scripts
```bash
# Mantener solo scripts esenciales
cd scripts/
mkdir maintenance/
mv run_migration.py load_firms_incremental.py aggregate_fire_episodes.py run_carousel_local.py maintenance/
# Eliminar resto de scripts de desarrollo
```

---

## Validación Post-Limpieza

### Checklist Crítico
- [ ] API inicia: `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`
- [ ] Frontend sirve: Acceder a `/` desde navegador
- [ ] Workers funcionan: `celery -A workers.celery_app worker --loglevel=info`
- [ ] Base de datos conecta: `python scripts/maintenance/run_migration.py`
- [ ] Logs se generan: Revisar `/var/log/forestguard/`

### Comandos de Verificación
```bash
# Verificar espacio disponible
df -h

# Verificar servicios activos
systemctl status forestguard nginx redis

# Probar API
curl -f http://localhost:8000/health

# Verificar frontend
curl -I http://localhost/ | grep "200 OK"
```

---

## Resumen de Ahorro de Espacio

| Categoría | Espacio Actual | Espacio Optimizado | Ahorro |
|-----------|----------------|-------------------|--------|
| Entornos Virtuales | 1,145.26 MB | 0 MB | 1,145.26 MB |
| Caches | 72.43 MB | 0 MB | 72.43 MB |
| Frontend (dev) | 349.20 MB | 2 MB | 347.20 MB |
| Temporales | 61.37 MB | 0 MB | 61.37 MB |
| Debug/Tests | ~1 MB | 0 MB | ~1 MB |
| **TOTAL** | **1,629 MB** | **~10 MB** | **~1,619 MB** |

**Reducción total**: ~99.4% del espacio utilizado

---

## Recomendaciones Finales

1. **Inmediato**: Eliminar entornos virtuales y caches (1.2 GB)
2. **Opcional**: Mantener documentación si se necesita referencia
3. **Mantenimiento**: Configurar rotación automática de logs
4. **Monitoreo**: Establecer alertas de uso de disco
5. **Backup**: Guardar `.env` y configs antes de limpieza

---

## Comandos de Mantenimiento Continuo

### Rotación de Logs (agregar a cron)
```bash
# /etc/logrotate.d/forestguard
/var/log/forestguard/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    postrotate
        systemctl reload forestguard
    endscript
}
```

### Limpieza Automática (semanal)
```bash
#!/bin/bash
# /opt/forestguard/cleanup.sh
find /opt/forestguard/logs/ -name "*.log" -mtime +7 -delete
find /opt/forestguard/temp_files/ -mtime +1 -delete
```
