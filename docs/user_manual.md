# 🌲 ForestGuard - User Manual

## 1. Introduction

**ForestGuard** is a geospatial intelligence platform designed for the monitoring, auditing, and legal enforcement of wildfire recovery in Argentina.

It combines satellite data (NASA FIRMS, Sentinel-2), climate data (ERA5-Land), and advanced AI analysis to provide accurate evidence for environmental protection laws.

### Access the platform
- **Production URL**: [https://forestguard.freedynamicdns.org](https://forestguard.freedynamicdns.org)
- **API Documentation**: [https://forestguard.freedynamicdns.org/docs](https://forestguard.freedynamicdns.org/docs)

---

## 2. Default public access (no login required)

Any citizen can access basic information without registering.

### 🔍 View active fires
Browse the interactive map to see active fire hotspots detected in the last 24-48 hours.
- **URL**: `Under construction`
- **Data Source**: NASA FIRMS (VIIRS/MODIS)

### ✅ Verify a certificate
If you have a customized ForestGuard certificate (PDF), you can verify its authenticity using its unique hash.
- **Endpoint**: `GET /api/v1/certificates/verify/{certificate_number}`
- **How to use**: Enter the alphanumeric code found at the bottom of the PDF.

---

## 3. For legal professionals (Escribanos & Lawyers)

*Requires API Key or Account*

### 📋 Land use audit (UC-01)
The core feature for verifying if a plot of land has fire-related prohibitions (e.g., cannot be sold or changed in land use for 60 years).

**How to request:**
1. Identify the coordinates (Latitude/Longitude) of the center of the plot.
2. Send a request to the audit endpoint.

**Example request:**
```json
POST /api/v1/audit/land-use
{
  "latitude": -31.4201,
  "longitude": -64.1888,
  "radius_meters": 500
}
```

**Understanding the result:**
- **is_prohibited**: `true` means fire was detected, and legal restrictions apply.
- **prohibition_until**: The date when the restriction expires (usually 30-60 years).
- **evidence**: List of fire events found intersecting the area.

### 📜 Request legal certificate (UC-07)
Generate a signed, downloadable PDF certificate summarizing the fire history of a specific location.

**Usage:**
1. Perform an audit first to get the `audit_id`.
2. Request a certificate for that audit.
3. Download the PDF using the returned URL.

---

## 4. For administrators (Forestry Service)

### 🌿 Vegetation recovery monitoring (UC-06)
Monitor how burnt areas are recovering over time using Vegetation Analysis Engine (VAE).
- **Metric**: NDVI (Normalized Difference Vegetation Index).
- **Goal**: Ensure native forest is recovering and not being replaced by crops or livestock.
- **Alerts**: The system flags areas with "Anomalous Recovery" (e.g., sudden drop in greenness indicating new clearing).

### 🕵️ Illegal land use detection (UC-08)
Automated scanning of protected areas to detect unauthorized land use changes after a fire.
- **Mechanism**: The system compares pre-fire and post-fire satellite imagery.
- **Action**: Generates a "Violation Alert" if agriculture is detected in a protected zone.

### 📊 Historical reports (UC-11)
Generate aggregated reports for statistical analysis or court cases.
- **Filters**: Date range, Province, Protected Area.
- **Output**: CSV or Excel export of all fire events.

---

## 5. API usage guide (for developers)

### Authentication
Include your API Key in the `Authorization` header:
```bash
Authorization: Bearer <your_access_token>
```

### Rate limits
- **Public**: 100 requests per minute per IP.
- **Authenticated**: 1000 requests per minute.

### Common endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Check system status |
| `POST` | `/api/v1/audit/land-use` | Check fire prohibitions |
| `GET` | `/api/v1/fires/{id}` | Get details of a specific fire |
| `POST` | `/api/v1/certificates/request` | Generate PDF certificate |
| `GET` | `/api/v1/monitoring/recovery/{fire_id}` | Get vegetation recovery timeline |
| `POST` | `/api/v1/reports/judicial` | Generate forensic judicial report |
| `POST` | `/api/v1/reports/historical` | Generate historical fire report |
| `POST` | `/api/v1/citizen/submit` | Submit citizen report |
| `GET` | `/api/v1/quality/fire-event/{id}` | Get data quality metrics |
| `GET` | `/api/v1/analysis/recurrence` | Analyze fire recurrence patterns |
| `GET` | `/api/v1/analysis/trends` | Get historical fire trends |

### Error codes
- `400 Bad Request`: Invalid coordinates or parameters.
- `401 Unauthorized`: Missing or invalid API Key.
- `429 Too Many Requests`: Slow down, rate limit exceeded.
- `503 Service Unavailable`: External service (NASA/Google) is down.

---

## 6. Email notifications

ForestGuard sends email notifications for the following events:

| Event | Recipients | Trigger |
|-------|------------|---------|
| Citizen Report Submitted | Administrators | New UC-09 report received |
| Land Use Violation Detected | Administrators | UC-08 detects illegal activity |
| Security Alert | Admin | Rate limit exceeded or suspicious activity |

### Changing email recipients

All email addresses are centralized in a single configuration file:

```
app/core/email_config.py
```

To update notification recipients, modify the appropriate variable in this file:

```python
# Example: Change admin email
ADMIN_EMAIL = "your-email@domain.com"

# Example: Add multiple citizen report recipients
CITIZEN_REPORTS_NOTIFY = ["email1@domain.com", "email2@domain.com"]
```

After modifying, restart the application for changes to take effect.

---

**Support**: contact@forestguard.ar

