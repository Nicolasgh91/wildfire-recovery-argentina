# Vestigia

Vestigia te ayuda a explorar incendios historicos en Argentina con evidencia satelital, sin necesitar perfil tecnico.

## propuesta de valor en 10 segundos

- miras incendios historicos y recientes en un solo lugar
- comparas antes/despues con imagenes satelitales
- generas evidencia descargable para compartir o investigar
- si lo necesitas, accedes a verificacion de terreno como modulo avanzado

## que se puede hacer hoy

- explorar incendios desde `/exploracion` con flujo guiado
- revisar historial con filtros y estadisticas en `/fires/history`
- visualizar episodios en mapa con datos reales en `/map`
- generar assets HD y PDF en flujo de exploracion/reportes
- usar verificar terreno (`/audit`) con login
- cargar creditos y usar checkout de pagos (con caveats)

## estado real del producto

- ✅ listo en produccion: exploracion, historial, mapa, assets HD/PDF, verificar terreno, contacto
- 🟡 implementado con caveats: MercadoPago, certificados, citizen report, shelters
- ⏳ en progreso: VAE como experiencia final de producto
- ❌ descartado/post-MVP: narrativa principal centrada en "auditoria legal"

Detalle completo:

- `docs/product/estado-real-del-producto.md`

## limitaciones honestas

- MercadoPago esta implementado, pero aun se opera con caveats de entorno y retorno.
- En frontend, citizen report todavia tiene envio simulado.
- Certificates en frontend sigue en modo mock y con feature flag.
- Shelters/visitor logs existen, pero permanecen bajo feature flag por defecto.

## casos de uso y estado (extracto)

Fuente canonica:

- `docs/product/casos-de-uso-y-estado.md`

Resumen rapido:

| UC | nombre | estado |
|---|---|---|
| UC-F03 | historico y dashboard | ✅ |
| UC-F06 | verificar terreno (modulo avanzado) | ✅ |
| UC-F08 | carrusel satelital | ✅ |
| UC-F11 | exploracion y reportes especializados | ✅ |
| UC-F10 | certificados monetizados | 🟡 |
| UC-F12 | recuperacion/cambio de uso (VAE) | ⏳ |

## arquitectura en una pantalla

- frontend: React + Vite
- api: FastAPI
- workers: Celery + Redis
- base de datos: PostgreSQL/PostGIS (Supabase)
- imagenes y reportes: object storage + pipeline satelital
- datos publicos: NASA FIRMS, Sentinel-2/GEE, Open-Meteo

Documentacion tecnica:

- `docs/frontend/README.md`
- `docs/backend/api/auth_matrix.md`
- `docs/infrastructure/deployment/DEPLOYMENT.md`
- `docs/containers/README.md` (arquitectura de contenedores y workers)

## como correr local

### opcion 1: docker (recomendada)

```bash
docker compose up -d
```

Servicios esperados:

- API: `http://localhost:8000/docs`
- Frontend: `http://localhost:5173`

### opcion 2: manual

```bash
# backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# frontend
cd frontend
npm install
npm run dev
```

Variables de entorno de referencia:

- `./.env.template`
- `frontend/.env.example`

## como se despliega hoy

- deploy principal automatizado por GitHub Actions hacia VM de produccion
- script operativo principal: `scripts/deploy.sh`
- flujo resumido: `docs/flujo-deploy.md`
- guia de deployment: `docs/infrastructure/deployment/DEPLOYMENT.md`

## diferenciacion

Hay dashboards globales y herramientas de monitoreo/alerta, pero Vestigia apunta a una experiencia guiada para usuario general con foco en investigacion reproducible.

Detalle con fuentes:

- `docs/product/diferenciacion-mercado.md`

## indice de documentacion

- indice general: `docs/INDEX.md`
- hub de producto: `docs/product/README.md`
- archivo historico: `docs/archive/`

## nota de alcance

Vestigia prioriza exploracion e investigacion guiada. El componente legal existe y se mantiene como capacidad avanzada, no como narrativa principal de entrada.


### Paleta principal de colores de la UI

🌟 Colores Principales (Light Mode)
Primary (Acción principal): hsl(155 55% 45%) — Un verde esmeralda vibrante.
Secondary (Acción secundaria): hsl(40 20% 35%) — Un marrón cálido oscuro.
Accent (Destacados): hsl(40 60% 70%) — Un tono arena/dorado suave.
Destructive (Errores/Peligro): hsl(0 84% 60%) — Rojo intenso.
Background (Fondo global): hsl(164 86% 16%) — Un verde bosque muy oscuro.
Foreground (Texto principal): hsl(40 10% 20%) — Casi negro con matiz cálido.
🌑 Modo Oscuro (Dark Mode)
Background: hsl(40 10% 18%) — Gris oscuro cálido.
Foreground: hsl(100 10% 95%) — Blanco con ligero matiz verdoso.
Primary: Se mantiene igual (hsl(155 55% 45%)).
Secondary: hsl(40 25% 45%).
Destructive: hsl(0 65% 50%).
🛠️ Elementos de UI y Bordes
Border: hsl(110 10% 88%) (Light) / hsl(40 10% 32%) (Dark).
Input: hsl(110 10% 92%) (Light) / hsl(40 10% 28%) (Dark).
Ring (Outline/Foco): Usa el color Primary.
⚓ Componentes Específicos
Nav (Barra de navegación): hsl(164 26% 68%).
Footer: hsl(164 86% 16%) (mismo que el fondo oscuro de la app).
Muted (Texto/fondos sutiles): hsl(100 10% 95%) (Light) / hsl(40 10% 28%) (Dark).
Si necesitas los valores exactos para algún componente de Shadcn o un gráfico específico (Charts 1-5), también están disponibles en el archivo de estilos.