# flujo de deploy a produccion

Principio base:

- el despliegue de aplicacion va por Git -> GitHub Actions -> VM
- los secretos de runtime se mantienen en `.env` de la VM

## flujo normal

1. trabajar en rama
2. abrir PR y merge a `main`
3. se dispara workflow `deploy-prod-vm.yml`
4. la VM actualiza codigo y ejecuta `scripts/deploy.sh`
5. validar salud (`/health`) y revisar logs si hace falta

## cuando hay cambios de frontend

- el build/push de imagen pasa por `frontend-build.yml`
- luego deploy en VM hace pull y up de servicios

## cuando hay cambios de backend/workers

- deploy actualiza repo en VM y reinicia stack por compose

## cambios en `.env` de la VM

No se despliegan desde git.

- editar manualmente en VM
- reiniciar servicios afectados

## checks rapidos

```bash
# en VM
docker compose ps
curl -L http://localhost/health
docker compose logs --tail=100 api
```

## docs relacionadas

- `docs/infrastructure/deployment/DEPLOYMENT.md`
- `.github/workflows/deploy-prod-vm.yml`
- `scripts/deploy.sh`
