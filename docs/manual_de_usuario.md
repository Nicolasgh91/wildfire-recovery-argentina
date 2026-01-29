# 🌲 ForestGuard - Manual de Usuario

## 1. Introducción

**ForestGuard** es una plataforma de inteligencia geoespacial diseñada para el monitoreo, auditoría y fiscalización de la recuperación de incendios forestales en Argentina.

Combina datos satelitales (NASA FIRMS, Sentinel-2), datos climáticos (ERA5-Land) y análisis avanzado de IA para proporcionar evidencia precisa para las leyes de protección ambiental (Ley de Manejo del Fuego).

### Acceso a la plataforma
- **URL de Producción**: [https://forestguard.freedynamicdns.org](https://forestguard.freedynamicdns.org)
- **Documentación API**: [https://forestguard.freedynamicdns.org/docs](https://forestguard.freedynamicdns.org/docs)

---

## 2. Acceso público (sin login)

Cualquier ciudadano puede acceder a información básica sin registrarse.

### 🔍 Ver incendios activos
Navegue por el mapa interactivo para ver los focos de calor detectados en las últimas 24-48 horas.
- **URL**: `Under construction`
- **Fuente de Datos**: NASA FIRMS (VIIRS/MODIS)

### ✅ Verificar un certificado
Si tiene un certificado forestal ForestGuard (PDF), puede verificar su autenticidad usando su código único (hash).
- **Endpoint**: `GET /api/v1/certificates/verify/{certificate_number}`
- **Cómo usar**: Ingrese el código alfanumérico que se encuentra al pie del PDF.

---

## 3. Para profesionales legales (escribanos y abogados)

*Requiere API Key o Cuenta*

### 📋 Auditoría de uso del suelo (UC-01)
La función principal para verificar si un terreno tiene prohibiciones relacionadas con incendios (ej. prohibición de venta o cambio de uso por 60 años).

**Cómo solicitar una auditoría:**
1. Identifique las coordenadas (Latitud/Longitud) del centro del terreno.
2. Envíe una solicitud al endpoint de auditoría.

**Ejemplo de solicitud:**
```json
POST /api/v1/audit/land-use
{
  "latitude": -31.4201,
  "longitude": -64.1888,
  "radius_meters": 500
}
```

**Interpretación del resultado:**
- **is_prohibited**: `true` significa que se detectó fuego y aplican restricciones legales.
- **prohibition_until**: La fecha de vencimiento de la prohibición (generalmente 30-60 años).
- **evidence**: Lista de eventos de incendio que intersectan con el área.

### 📜 Solicitar certificado legal (UC-07)
Genere un certificado PDF firmado y descargable que resume el historial de incendios de una ubicación específica.

**Uso:**
1. Realice una auditoría primero para obtener el `audit_id`.
2. Solicite un certificado para esa auditoría.
3. Descargue el PDF usando la URL proporcionada.

---

## 4. Para administradores (servicio forestal)

### 🌿 Monitoreo de recuperación de vegetación (UC-06)
Monitoree cómo se recuperan las áreas quemadas a lo largo del tiempo utilizando el Motor de Análisis de Vegetación (VAE).
- **Métrica**: NDVI (Índice de Vegetación de Diferencia Normalizada).
- **Objetivo**: Asegurar que el bosque nativo se recupere y no sea reemplazado por cultivos o ganado.
- **Alertas**: El sistema marca áreas con "Recuperación Anómala" (ej. caída repentina del verde indicando desmonte).

### 🕵️ Detección de uso ilegal (UC-08)
Escaneo automatizado de áreas protegidas para detectar cambios de uso no autorizados post-incendio.
- **Mecanismo**: El sistema compara imágenes satelitales pre-fuego y post-fuego.
- **Acción**: Genera una "Alerta de Violación" si se detecta agricultura en una zona protegida.

### 📊 Reportes históricos (UC-11)
Genere reportes agregados para análisis estadístico o casos judiciales.
- **Filtros**: Rango de fechas, Provincia, Área Protegida.
- **Salida**: Exportación a CSV o Excel de todos los eventos de incendio.

---

## 5. Guía de uso de API (para desarrolladores)

### Autenticación
Incluya su API Key en el header `Authorization`:
```bash
Authorization: Bearer <your_access_token>
```

### Límites de tasa (rate limits)
- **Público**: 100 peticiones por minuto por IP.
- **Autenticado**: 1000 peticiones por minuto.

### Endpoints comunes

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/health` | Verificar estado del sistema |
| `POST` | `/api/v1/audit/land-use` | Verificar prohibiciones de fuego |
| `GET` | `/api/v1/fires/{id}` | Obtener detalles de un incendio |
| `POST` | `/api/v1/certificates/request` | Generar certificado PDF |
| `GET` | `/api/v1/monitoring/recovery/{fire_id}` | Obtener línea de tiempo de recuperación |
| `POST` | `/api/v1/reports/judicial` | Generar reporte pericial forense |
| `POST` | `/api/v1/reports/historical` | Generar reporte histórico de incendios |
| `POST` | `/api/v1/citizen/submit` | Enviar denuncia ciudadana |
| `GET` | `/api/v1/quality/fire-event/{id}` | Obtener métricas de calidad de datos |
| `GET` | `/api/v1/analysis/recurrence` | Analizar patrones de recurrencia |
| `GET` | `/api/v1/analysis/trends` | Obtener tendencias históricas |

### Códigos de error
- `400 Bad Request`: Coordenadas o parámetros inválidos.
- `401 Unauthorized`: API Key faltante o inválida.
- `429 Too Many Requests`: Límite de tasa excedido, espere unos segundos.
- `503 Service Unavailable`: Servicio externo (NASA/Google) no disponible.

---

## 6. Notificaciones por email

ForestGuard envía notificaciones por email para los siguientes eventos:

| Evento | Destinatarios | Disparador |
|--------|---------------|------------|
| Denuncia Ciudadana Recibida | Administradores | Nueva denuncia UC-09 recibida |
| Violación de Uso de Suelo Detectada | Administradores | UC-08 detecta actividad ilegal |
| Alerta de Seguridad | Admin | Límite de tasa excedido o actividad sospechosa |

### Cambiar destinatarios de email

Todas las direcciones de email están centralizadas en un único archivo de configuración:

```
app/core/email_config.py
```

Para actualizar los destinatarios, modifique la variable correspondiente en este archivo:

```python
# Ejemplo: Cambiar email de administrador
ADMIN_EMAIL = "tu-email@dominio.com"

# Ejemplo: Agregar múltiples destinatarios para denuncias ciudadanas
CITIZEN_REPORTS_NOTIFY = ["email1@dominio.com", "email2@dominio.com"]
```

Después de modificar, reinicie la aplicación para que los cambios surtan efecto.

---

**Soporte**: contacto@forestguard.ar

