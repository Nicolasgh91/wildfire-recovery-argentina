# guia de despliegue de Vestigia

Esta guia prioriza el camino simple y actual para operar la app.

## resumen operativo

- entorno objetivo: VM Oracle Cloud
- despliegue: Docker Compose + script `scripts/deploy.sh`
- automatizacion: GitHub Actions (`deploy-prod-vm.yml`)
- secretos de runtime: `.env` en la VM (no en el repo)

## prerequisitos

- VM Linux con Docker y Docker Compose
- dominio y SSL configurados
- archivo `.env` en la VM con claves reales
- repo clonado en `/home/opc`

## flujo recomendado (produccion)

1. push y merge a `main`
2. workflow de deploy ejecuta SSH a VM
3. en VM:
   - `git pull --ff-only`
   - `./scripts/deploy.sh`
4. healthcheck:
   - `curl -L http://localhost/health`

Referencias:

- `scripts/deploy.sh`
- `.github/workflows/deploy-prod-vm.yml`
- `docs/flujo-deploy.md`

## flujo local rapido

```bash
docker compose up -d
```

Servicios utiles:

- API: `http://localhost:8000/docs`
- frontend: `http://localhost:5173`

## configuracion de entorno

Plantilla base:

- `./.env.template`

Variables clave:

- DB, Supabase, Redis/Celery
- storage backend
- FIRMS/GEE
- MercadoPago (`MP_*`, `PAYMENT_*_URL`)

## limitaciones y caveats

- MercadoPago en produccion depende de webhook valido y retorno consistente.
- algunos modulos estan condicionados por feature flags frontend.
- certificados SSL y DNS deben estar estables antes de primer deploy automatizado.

## troubleshooting minimo

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

Si necesitas comandos mas detallados o escenarios de emergencia, revisar:

- `docs/infrastructure/deployment/quick-deployment-commands.md`
- `docs/infrastructure/deployment/quick-fixes.md`
- `docs/infrastructure/deployment/immediate-fix.md`
