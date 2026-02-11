# Verificación manual de `generate_carousel`

Fecha: 2026-02-11 16:39:10Z

## 1) Ejecución manual del task

Comando documentado en `scripts/carousel_manual_run.md`:

```bash
celery -A workers.celery_app call workers.tasks.carousel_task.generate_carousel --kwargs='{"force_refresh": true}'
```

Resultado en este entorno: **falló** por falta de resolución del host `redis` (`kombu.exceptions.OperationalError: Error -2 connecting to redis:6379`).

## 2) Verificación en DB (`fire_episodes.slides_data`, `fire_events.slides_data`)

Intentos realizados:

- `psql "$DATABASE_URL" -c "SELECT COUNT(*) FROM fire_episodes WHERE jsonb_array_length(slides_data) > 0;"` → `psql` no está instalado en el contenedor.
- Script Python con SQLAlchemy para consultar ambos conteos → `DATABASE_URL set: False`.

Conclusión: no fue posible verificar en DB en este entorno por falta de cliente (`psql`) y de credenciales/conexión (`DATABASE_URL`).

## 3) Verificación en bucket GCS de `thumbnail_url/url`

Variables de entorno verificadas:

- `GCS_PROJECT_ID=None`
- `GCS_SERVICE_ACCOUNT_JSON=None`
- `GOOGLE_APPLICATION_CREDENTIALS=None`
- `STORAGE_BUCKET_IMAGES=None`

Conclusión: no hay credenciales ni bucket configurado para validar objetos GCS desde este entorno.

## 4) Confirmación desde frontend Home (revisión de código)

Se validó por lectura estática:

- Home obtiene episodios activos/recientes y los pasa a `FireCard` (`frontend/src/pages/Home.tsx`).
- `FireCard` filtra `fire.slides_data` por `thumbnail_url || url`.
- Si existen slides, renderiza `<img src={slideUrl}>` dentro de un carousel.
- Si no hay slides, muestra fallback con ícono de llama.
- `StoriesBar` actualmente no renderiza `slides_data`; muestra indicadores de severidad por FRP.

## Estado final

- Ejecución de task: ❌ bloqueada por Redis no resolvible en este entorno.
- Verificación DB: ❌ bloqueada por `DATABASE_URL` ausente y `psql` faltante.
- Verificación GCS: ❌ bloqueada por credenciales/bucket no configurados.
- Verificación frontend: ✅ confirmada por revisión de código (flujo de render existe en `FireCard`).
