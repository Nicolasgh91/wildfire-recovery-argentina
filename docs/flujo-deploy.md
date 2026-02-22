# Flujo de trabajo para despliegue a producción

## Principio fundamental

> Los cambios en local **nunca se bajan manualmente a la VM**. Todo pasa por Git → GitHub → workflow automático.

---

## Caso 1: cambios en el frontend

```
1. Desarrollar en local
2. git add / commit / push → rama feature
3. Abrir PR hacia main → hacer merge
4. GitHub dispara automáticamente:
   a. frontend-build.yml → construye imagen Docker → la sube a GHCR
   b. deploy-prod-vm.yml → SSH a la VM → git pull → deploy.sh
      → docker compose pull frontend → docker compose up -d
5. Verificar en https://forestguard.freedynamicdns.org
```

**Si los cambios no se ven en producción después del deploy:**
```bash
# Hard refresh en el navegador (Ctrl+Shift+R / Cmd+Shift+R)
# Si sigue igual, verificar que la imagen nueva se descargó:
docker compose images | grep frontend
# La columna "CREATED" debe mostrar la fecha del último build
```

---

## Caso 2: cambios en el backend (API / workers)

```
1. Desarrollar en local
2. git add / commit / push → rama feature
3. Abrir PR hacia main → hacer merge
4. GitHub dispara automáticamente deploy-prod-vm.yml:
   → SSH a la VM → git pull → deploy.sh
   → docker compose build api → docker compose up -d
5. Verificar: curl https://forestguard.freedynamicdns.org/health
```

---

## Caso 3: cambios en el .env de la VM (variables de entorno)

El `.env` **no está en el repo** y no se despliega automáticamente.
Hay que editarlo manualmente en la VM:

```bash
ssh opc@<VM_IP>
nano /home/opc/.env
# Editar la variable necesaria
docker compose restart api   # o el servicio afectado
```

---

## Caso 4: nueva imagen del frontend no se descarga en la VM

El `docker compose pull` solo funciona si la imagen viene de GHCR.
Si el `docker-compose.yml` tiene `build:` en vez de `image:`, la VM
construye localmente y nunca descarga la nueva imagen de GHCR.

**Verificación:**
```bash
grep -A2 "frontend:" /home/opc/docker-compose.yml
# Debe decir:
#   image: ghcr.io/nicolasgh91/wildfire-recovery-argentina/frontend:latest
# NO debe decir:
#   build: ...
```

**Si la VM no tiene credenciales para GHCR:**
```bash
echo "TU_GITHUB_TOKEN" | docker login ghcr.io -u Nicolasgh91 --password-stdin
```

---

## Diagrama del flujo completo

```
LOCAL                     GITHUB                        VM (producción)
──────                    ──────                        ───────────────
git push
  │
  └──► PR → merge main
              │
              ├──► frontend-build.yml
              │      Build imagen Docker
              │      Push → ghcr.io/.../frontend:latest
              │
              └──► deploy-prod-vm.yml
                     SSH a la VM
                       git pull origin main
                       deploy.sh
                         docker compose pull frontend  ← descarga nueva imagen
                         docker compose up -d          ← reinicia contenedores
                         health check /health
```

---

## Checklist ante cualquier problema de deploy

```
[ ] ¿El workflow de GitHub Actions terminó con tilde verde?
[ ] ¿El paso "Build Frontend Image" corrió y publicó imagen nueva?
[ ] ¿El deploy-prod-vm.yml completó el health check?
[ ] ¿La imagen del frontend en la VM es reciente? (docker compose images)
[ ] ¿El navegador tiene caché vieja? (Ctrl+Shift+R)
[ ] ¿Hay errores en consola del navegador? (F12 → Console)
[ ] ¿La API responde? (curl https://forestguard.freedynamicdns.org/health)
```

---

## Comandos útiles en la VM

```bash
# Ver estado de todos los contenedores
docker compose ps

# Ver logs de un servicio
docker compose logs --tail=30 api
docker compose logs --tail=30 frontend
docker compose logs --tail=30 nginx

# Forzar descarga de imagen nueva del frontend
docker compose pull frontend
docker compose up -d frontend

# Reiniciar un servicio sin rebuild
docker compose restart api

# Rebuild completo del backend (si hay cambios en requirements.txt)
docker compose build --no-cache api
docker compose up -d api
```
