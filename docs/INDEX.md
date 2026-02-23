# indice de documentacion

Ultima actualizacion: 22 de febrero de 2026.

Este indice separa documentacion vigente (canonica) de documentacion historica (archivo).

## documentacion canonica actual

### producto

- `docs/product/README.md` - hub canonico de producto
- `docs/product/casos-de-uso-y-estado.md` - fuente unica de casos de uso y estado
- `docs/product/estado-real-del-producto.md` - semaforo de estado y top 5 de cierre
- `docs/product/diferenciacion-mercado.md` - relevamiento externo con citas
- `docs/product/matriz-inconsistencias-2026-02-22.md` - diagnostico de consistencia

### experiencia frontend

- `docs/frontend/README.md` - rutas, estado por pantalla y caveats
- `docs/frontend/routing_access_ruc.md` - matriz de acceso por ruta

### contratos API y auth

- `docs/backend/api/auth_matrix.md` - matriz de autenticacion por endpoint

### infraestructura y operacion

- `docs/infrastructure/deployment/DEPLOYMENT.md` - guia de despliegue
- `docs/flujo-deploy.md` - flujo resumido de deploy y troubleshooting operativo

### referencia de marca

- `docs/brand.md` - configuracion de branding (Vestigia)

## documentacion historica (archivo)

- `docs/archive/` - roadmaps, planes tecnicos y reportes historicos migrados

Regla:

- si una ruta vieja fue migrada, el archivo original queda como puente con link al archivo y al canónico.

## reglas de lectura rapida

1. si queres entender el producto hoy: empezar por `README.md` y `docs/product/estado-real-del-producto.md`.
2. si queres validar estado real contra codigo: usar `docs/product/casos-de-uso-y-estado.md` + `docs/backend/api/auth_matrix.md`.
3. si queres contexto historico: ir a `docs/archive/`.
