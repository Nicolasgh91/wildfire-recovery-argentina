# Backlog de tareas de documentación y deuda técnica

## Frontend

- Revisar y reducir tamaño de bundles principales, mejorando code splitting por ruta.
- Unificar estrategia de imports estáticos y dinámicos para módulos compartidos (por ejemplo, componentes de tarjetas y cliente de Supabase).

## Seguridad

- Revisar y ajustar export a GraphML en scripts de ownership para serializar atributos complejos como cadenas JSON.
- Verificar cabeceras de seguridad (HSTS, CSP, X-Content-Type-Options) en entorno productivo y alinear configuración de nginx.
- Añadir verificación en entorno de producción para asegurar que el rate limiter nunca cae en backend en memoria.
- Planificar migración de modelos y validadores a Pydantic V2 evitando avisos de deprecación.

## UC-F12 y VAE

- Diseñar y agregar tests automatizados para `VAEService` y workers asociados, cubriendo casos de recuperación, cambios de uso y anomalías.
- Revisar y documentar formalmente la semántica de `recovery_percentage` y alinear umbrales de clasificación entre VAE, workers, API y frontend.
- Diferenciar estados `pending` por falta de datos GEE de estados en cola y reflejarlo en respuestas de API.
- Definir y documentar un conjunto mínimo de casos reales para validar heurísticas de cambio de uso de suelo.
- Verificar en entorno real la configuración de RLS y roles de Supabase para escritura y lectura en tablas de monitoreo.

## Colas y workers

- Revisar y alinear configuración de colas Celery (`gee`, `analysis`, `vae`) con los workers definidos en `docker-compose` para evitar tareas sin consumidor.

Las tareas completadas de este backlog deben migrarse a los registros de decisiones en `docs/decisions/` cuando se implementen y verifiquen.
