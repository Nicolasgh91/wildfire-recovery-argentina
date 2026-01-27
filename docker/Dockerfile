# =============================================================================
# FORESTGUARD API - DOCKERFILE
# =============================================================================
# Imagen Docker para la API FastAPI.
#
# Build:
#   docker build -f Dockerfile -t forestguard-api .
#
# Run:
#   docker run -p 8000:8000 --env-file .env forestguard-api
#
# Multi-stage build para imagen más pequeña (~200MB vs ~1GB)
# =============================================================================

# -----------------------------------------------------------------------------
# STAGE 1: Builder (instala dependencias)
# -----------------------------------------------------------------------------
FROM python:3.11-slim as builder

# Variables de entorno para Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Instalar dependencias de sistema para compilar paquetes
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libgeos-dev \
    libproj-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar solo requirements para cachear layer
COPY requirements.txt .

# Crear virtualenv e instalar dependencias
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip && \
    pip install -r requirements.txt


# -----------------------------------------------------------------------------
# STAGE 2: Runtime (imagen final)
# -----------------------------------------------------------------------------
FROM python:3.11-slim as runtime

# Metadata
LABEL maintainer="ForestGuard Team <contact@forestguard.ar>"
LABEL description="ForestGuard API - Fiscalización de incendios forestales"
LABEL version="0.2.0"

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Usar virtualenv del builder
    PATH="/opt/venv/bin:$PATH" \
    # Variables de la aplicación
    APP_ENV=production \
    HOST=0.0.0.0 \
    PORT=8000

WORKDIR /app

# Instalar solo dependencias de runtime (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libgeos-c1v5 \
    libproj25 \
    # Para WeasyPrint (PDFs)
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copiar virtualenv desde builder
COPY --from=builder /opt/venv /opt/venv

# Crear usuario no-root por seguridad
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

# Copiar código de la aplicación
COPY --chown=appuser:appuser . .

# Exponer puerto
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/api/v1/health')" || exit 1

# Comando por defecto (producción con Gunicorn)
CMD ["gunicorn", "app.main:app", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
