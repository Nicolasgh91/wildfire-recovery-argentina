# 🌲 ForestGuard - User Manual

## 1. Introduction

**ForestGuard** is a geospatial intelligence platform designed for the monitoring, auditing, and legal enforcement of wildfire recovery in Argentina.

It combines satellite data (NASA FIRMS, Sentinel-2), climate data (ERA5-Land), and advanced AI analysis to provide accurate evidence for environmental protection laws.

### Access the Platform
- **Production URL**: [https://forestguard.freedynamicdns.org](https://forestguard.freedynamicdns.org)
- **API Documentation**: [https://forestguard.freedynamicdns.org/docs](https://forestguard.freedynamicdns.org/docs)

---

## 2. Default Public Access (No Login Required)

Any citizen can access basic information without registering.

### 🔍 View Active Fires
Browse the interactive map to see active fire hotspots detected in the last 24-48 hours.
- **URL**: `Under construction`
- **Data Source**: NASA FIRMS (VIIRS/MODIS)

### ✅ Verify a Certificate
If you have a customized ForestGuard certificate (PDF), you can verify its authenticity using its unique hash.
- **Endpoint**: `GET /api/v1/certificates/verify/{certificate_number}`
- **How to use**: Enter the alphanumeric code found at the bottom of the PDF.

---

## 3. For Legal Professionals (Escribanos & Lawyers)

*Requires API Key or Account*

### 📋 Land Use Audit (UC-01)
The core feature for verifying if a plot of land has fire-related prohibitions (e.g., cannot be sold or changed in land use for 60 years).

**How to Request:**
1. Identify the coordinates (Latitude/Longitude) of the center of the plot.
2. Send a request to the audit endpoint.

**Example Request:**
```json
POST /api/v1/audit/land-use
{
  "latitude": -31.4201,
  "longitude": -64.1888,
  "radius_meters": 500
}
```

**Understanding the Result:**
- **is_prohibited**: `true` means fire was detected, and legal restrictions apply.
- **prohibition_until**: The date when the restriction expires (usually 30-60 years).
- **evidence**: List of fire events found intersecting the area.

### 📜 Request Legal Certificate (UC-07)
Generate a signed, downloadable PDF certificate summarizing the fire history of a specific location.

**Usage:**
1. Perform an audit first to get the `audit_id`.
2. Request a certificate for that audit.
3. Download the PDF using the returned URL.

---

## 4. For Administrators (Forestry Service)

### 🌿 Vegetation Recovery Monitoring (UC-06)
Monitor how burnt areas are recovering over time using Vegetation Analysis Engine (VAE).
- **Metric**: NDVI (Normalized Difference Vegetation Index).
- **Goal**: Ensure native forest is recovering and not being replaced by crops or livestock.
- **Alerts**: The system flags areas with "Anomalous Recovery" (e.g., sudden drop in greenness indicating new clearing).

### 🕵️ Illegal Land Use Detection (UC-08)
Automated scanning of protected areas to detect unauthorized land use changes after a fire.
- **Mechanism**: The system compares pre-fire and post-fire satellite imagery.
- **Action**: Generates a "Violation Alert" if agriculture is detected in a protected zone.

### 📊 Historical Reports (UC-11)
Generate aggregated reports for statistical analysis or court cases.
- **Filters**: Date range, Province, Protected Area.
- **Output**: CSV or Excel export of all fire events.

---

## 5. API Usage Guide (For Developers)

### Authentication
Include your API Key in the `Authorization` header:
```bash
Authorization: Bearer <your_access_token>
```

### Rate Limits
- **Public**: 100 requests per minute per IP.
- **Authenticated**: 1000 requests per minute.

### Common Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Check system status |
| `POST` | `/api/v1/audit/land-use` | Check fire prohibitions |
| `GET` | `/api/v1/fires/{id}` | Get details of a specific fire |
| `POST` | `/api/v1/certificates/request` | Generate PDF certificate |

### Error Codes
- `400 Bad Request`: Invalid coordinates or parameters.
- `401 Unauthorized`: Missing or invalid API Key.
- `429 Too Many Requests`: Slow down, rate limit exceeded.
- `503 Service Unavailable`: External service (NASA/Google) is down.

---

**Support**: contact@forestguard.ar
