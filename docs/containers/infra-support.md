## Contenedor `redis` (`forestguard-redis`)

El servicio `redis` provee **broker y result backend de Celery**, además de actuar como caché ligera si se necesita.

- **Servicio Compose**: `redis`
- **Nombre de contenedor**: `forestguard-redis`
- **Imagen**: `redis:7-alpine`
- **Volumen**: `redis_data:/data`

### Configuración en `docker-compose.yml`

- Comando:
  - `redis-server --appendonly yes --maxmemory 48mb --maxmemory-policy allkeys-lru`
- Recursos:
  - `mem_limit: 64m`
  - Límite de CPU: `1.0`
- Healthcheck:
  - `redis-cli ping`
- Logging:
  - `json-file` con `max-size: "10m"`, `max-file: "3"`.

### Dependencias

- **Consumido por**:
  - `api` (`CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`)
  - `worker-fast`
  - `worker-gee`
  - `celery-beat`
  - `flower`

### Datos que almacena

- Colas de tareas Celery (mensajes y resultados).
- Metadatos de scheduling (por ejemplo, estado de beat en algunos casos).
- Puede almacenar claves adicionales si la app/infra lo requiere, pero su uso principal es Celery.

### Consideraciones operativas

- El volumen `redis_data` persiste los datos entre reinicios de contenedor.
- Conviene:
  - Monitorear tamaño de `redis_data` si el volumen crece demasiado.
  - Asegurarse de que no se usen TTLs excesivamente largos para colas que puedan generar backlogs.

## Otros componentes de soporte

Actualmente no hay otros contenedores de soporte dedicados (por ejemplo, un contenedor de utilidades o cron genérico).  
Los scripts fuera de Celery (por ejemplo tareas de mantenimiento manual) se ejecutan típicamente vía:

- `docker compose exec api ...`
- Jobs manuales en la VM host.

Si en el futuro se agrega un contenedor de utilidades (por ejemplo `tools` o `maintenance-runner`), seguir este patrón de documentación:

- Describir:
  - Rol principal.
  - Scripts que ejecuta.
  - Dependencias (DB, Redis, storage).
  - Cómo se invoca (comando Compose, cron, etc.).

