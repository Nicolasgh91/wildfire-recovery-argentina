# 🌲 ForestGuard - Manual de Usuario

## 1. Introducción

**ForestGuard** es una plataforma de inteligencia geoespacial diseñada para el monitoreo, auditoría y fiscalización de la recuperación de incendios forestales en Argentina.

Combina datos satelitales (NASA FIRMS, Sentinel-2), datos climáticos (ERA5-Land) y análisis avanzado de IA para proporcionar evidencia precisa para las leyes de protección ambiental (Ley de Manejo del Fuego).

### Acceso a la Plataforma
- **URL de Producción**: [https://forestguard.freedynamicdns.org](https://forestguard.freedynamicdns.org)
- **Documentación API**: [https://forestguard.freedynamicdns.org/docs](https://forestguard.freedynamicdns.org/docs)

---

## 2. Acceso Público (Sin Login)

Cualquier ciudadano puede acceder a información básica sin registrarse.

### 🔍 Ver Incendios Activos
Navegue por el mapa interactivo para ver los focos de calor detectados en las últimas 24-48 horas.
- **URL**: `Under construction`
- **Fuente de Datos**: NASA FIRMS (VIIRS/MODIS)

### ✅ Verificar un Certificado
Si tiene un certificado forestal ForestGuard (PDF), puede verificar su autenticidad usando su código único (hash).
- **Endpoint**: `GET /api/v1/certificates/verify/{certificate_number}`
- **Cómo usar**: Ingrese el código alfanumérico que se encuentra al pie del PDF.

---

## 3. Para Profesionales Legales (Escribanos y Abogados)

*Requiere API Key o Cuenta*

### 📋 Auditoría de Uso del Suelo (UC-01)
La función principal para verificar si un terreno tiene prohibiciones relacionadas con incendios (ej. prohibición de venta o cambio de uso por 60 años).

**Cómo solicitar una auditoría:**
1. Identifique las coordenadas (Latitud/Longitud) del centro del terreno.
2. Envíe una solicitud al endpoint de auditoría.

**Ejemplo de Solicitud:**
```json
POST /api/v1/audit/land-use
{
  "latitude": -31.4201,
  "longitude": -64.1888,
  "radius_meters": 500
}
```

**Interpretación del Resultado:**
- **is_prohibited**: `true` significa que se detectó fuego y aplican restricciones legales.
- **prohibition_until**: La fecha de vencimiento de la prohibición (generalmente 30-60 años).
- **evidence**: Lista de eventos de incendio que intersectan con el área.

### 📜 Solicitar Certificado Legal (UC-07)
Genere un certificado PDF firmado y descargable que resume el historial de incendios de una ubicación específica.

**Uso:**
1. Realice una auditoría primero para obtener el `audit_id`.
2. Solicite un certificado para esa auditoría.
3. Descargue el PDF usando la URL proporcionada.

---

## 4. Para Administradores (Servicio Forestal)

### 🌿 Monitoreo de Recuperación de Vegetación (UC-06)
Monitoree cómo se recuperan las áreas quemadas a lo largo del tiempo utilizando el Motor de Análisis de Vegetación (VAE).
- **Métrica**: NDVI (Índice de Vegetación de Diferencia Normalizada).
- **Objetivo**: Asegurar que el bosque nativo se recupere y no sea reemplazado por cultivos o ganado.
- **Alertas**: El sistema marca áreas con "Recuperación Anómala" (ej. caída repentina del verde indicando desmonte).

### 🕵️ Detección de Uso Ilegal (UC-08)
Escaneo automatizado de áreas protegidas para detectar cambios de uso no autorizados post-incendio.
- **Mecanismo**: El sistema compara imágenes satelitales pre-fuego y post-fuego.
- **Acción**: Genera una "Alerta de Violación" si se detecta agricultura en una zona protegida.

### 📊 Reportes Históricos (UC-11)
Genere reportes agregados para análisis estadístico o casos judiciales.
- **Filtros**: Rango de fechas, Provincia, Área Protegida.
- **Salida**: Exportación a CSV o Excel de todos los eventos de incendio.

---

## 5. Guía de Uso de API (Para Desarrolladores)

### Autenticación
Incluya su API Key en el header `Authorization`:
```bash
Authorization: Bearer <your_access_token>
```

### Límites de Tasa (Rate Limits)
- **Público**: 100 peticiones por minuto por IP.
- **Autenticado**: 1000 peticiones por minuto.

### Endpoints Comunes

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/health` | Verificar estado del sistema |
| `POST` | `/api/v1/audit/land-use` | Verificar prohibiciones de fuego |
| `GET` | `/api/v1/fires/{id}` | Obtener detalles de un incendio |
| `POST` | `/api/v1/certificates/request` | Generar certificado PDF |

### Códigos de Error
- `400 Bad Request`: Coordenadas o parámetros inválidos.
- `401 Unauthorized`: API Key faltante o inválida.
- `429 Too Many Requests`: Límite de tasa excedido, espere unos segundos.
- `503 Service Unavailable`: Servicio externo (NASA/Google) no disponible.

---

**Soporte**: contacto@forestguard.ar
