Actúa como un arquitecto de software y experto en DevOps. Necesito que generes la configuración de Docker (Dockerfiles, docker-compose.yml y scripts de despliegue) para un nuevo proyecto. 

Para garantizar un entorno de producción optimizado, ligero y sin problemas de acumulación de basura, debes aplicar de forma estricta las siguientes directrices en todo el código generado:

1. Optimización de imágenes (Dockerfiles):
   - Implementa obligatoriamente "multi-stage builds". Crea una etapa "builder" para instalar herramientas de compilación pesadas (como `build-essential`) y una etapa "runtime" final limpia.
   - En la etapa runtime, instala solo las bibliotecas de ejecución estrictamente necesarias (por ejemplo, prioriza librerías como `libpq5` sobre clientes completos como `postgresql-client`).
   - Para aplicaciones Python, configura las variables de entorno `PYTHONDONTWRITEBYTECODE=1` y `PYTHONUNBUFFERED=1`.
   - Crea y utiliza un usuario sin privilegios de root (non-root user) para ejecutar los procesos por motivos de seguridad.
   - Define un `HEALTHCHECK` funcional para cada servicio. Evita utilizar interpolación de variables de entorno directamente en la directiva CMD del health check dentro del Dockerfile.

2. Orquestación (docker-compose.yml):
   - Nunca dejes variables de entorno hardcodeadas (especialmente las que definen el entorno, como "development"). Utiliza variables con valores por defecto seguros para producción, por ejemplo: `${ENVIRONMENT:-production}`.

3. Exclusión de archivos:
   - Proporciona un archivo `.dockerignore` completo que excluya explícitamente los scripts de despliegue, scripts de mantenimiento, archivos temporales y cualquier otro elemento que no sea requerido para la ejecución del contenedor.

4. Mantenimiento y despliegue (scripts y CI/CD):
   - Incluye rutinas de limpieza automáticas tanto en la etapa de pre-despliegue como en la de post-despliegue.
   - Los scripts deben ejecutar limpieza básica sistemática de contenedores detenidos e imágenes huérfanas (`dangling`).
   - Implementa un control de capacidad condicional: el script de despliegue debe leer el uso del disco y, si supera el 75%, ejecutar una limpieza agresiva que elimine la caché de BuildKit (`docker builder prune -af`) y las imágenes antiguas no utilizadas (`docker image prune -af --filter "until=168h"`).

Por favor, genera los archivos solicitados aplicando estos estándares.
