# 🔥 ForestGuard - Project Plan v2.0

## Current project status

```
📊 OVERALL PROGRESS: ██████████████░░░░░░ 70%

✅ COMPLETED:
├── SQL Schema v0.2 designed and validated
├── Documentation of 11 use cases (UC-01 to UC-11)
├── Hybrid architecture defined (API + VAE + ERS)
├── Branding guide
├── Complete architectural validation
├── Operational improvements (error handling, monitoring)
└── RLS policies and security

⏳ IN PROGRESS:
├── VAE/ERS services implementation
└── Missing endpoints (UC-02, UC-11)

🔜 PENDING:
├── FastAPI Backend (remaining endpoints)
├── Workers (Celery) - full implementation
├── React Frontend
└── Production deploy
```

---

## 📋 PHASE 1: Base infrastructure (week 1)

### 1.1 Supabase configuration
| # | Task | Subtask | Priority | Status | Estimate |
|---|------|---------|----------|--------|----------|
| 1.1.1 | Create Supabase project | - | 🔴 High | ✅ DONE | 10 min |
| 1.1.2 | Execute schema v0.2 | With UC-11, RLS policies | 🔴 High | ✅ DONE | 15 min |
| 1.1.3 | Verify PostGIS extensions | postgis, pg_trgm | 🔴 High | ✅ DONE | 5 min |
| 1.1.4 | Configure API keys | Generate anon + service role | 🔴 High | ⏳ PENDING | 5 min |
| 1.1.5 | Test connection | Run test query | 🔴 High | ⏳ PENDING | 10 min |

**Success criteria:** Schema loaded, 14 tables created (includes historical_report_requests), spatial query works

### 1.2 Backend project structure
| # | Task | Subtask | Priority | Status | Estimate |
|---|------|---------|----------|--------|----------|
| 1.2.1 | Create folder structure | app/, workers/, tests/ | 🔴 High | ✅ DONE | 30 min |
| 1.2.2 | Configure pyproject.toml | Dependencies + metadata | 🔴 High | ✅ DONE | 20 min |
| 1.2.3 | Create .env.example | Required variables | 🔴 High | ✅ DONE | 15 min |
| 1.2.4 | Setup SQLAlchemy + GeoAlchemy | Base models | 🔴 High | ⏳ PENDING | 1h |
| 1.2.5 | Configure Alembic | Migrations | 🟡 Medium | 🔜 PENDING | 45 min |

**Success criteria:** `python -m app.main` starts without errors

### 1.3 Docker & DevOps
| # | Task | Subtask | Priority | Status | Estimate |
|---|------|---------|----------|--------|----------|
| 1.3.1 | Dockerfile.api | FastAPI + Gunicorn | 🔴 High | ✅ DONE | 30 min |
| 1.3.2 | Dockerfile.worker | Celery + dependencies | 🔴 High | ✅ DONE | 30 min |
| 1.3.3 | docker-compose.yml | Dev environment | 🔴 High | ✅ DONE | 45 min |
| 1.3.4 | Configure Redis | Cache + Celery broker | 🟡 Medium | ✅ DONE | 20 min |
| 1.3.5 | Makefile | Useful commands | 🟢 Low | ✅ DONE | 20 min |

**Success criteria:** `docker-compose up` starts all services

---

## 📋 PHASE 2: Data ingestion (week 2)

### 2.1 NASA FIRMS script
| # | Task | Subtask | Priority | Status | Estimate |
|---|------|---------|----------|--------|----------|
| 2.1.1 | Download bulk CSV | 2024 VIIRS Argentina | 🔴 High | ✅ DONE | 30 min |
| 2.1.2 | CSV Parser | Map columns to schema | 🔴 High | ✅ DONE | 1h |
| 2.1.3 | Quality filter | confidence >= 80% | 🔴 High | ✅ DONE | 30 min |
| 2.1.4 | Batch insertion | 10k records in < 30s | 🔴 High | ✅ DONE | 1h |
| 2.1.5 | Validation | No duplicates, valid geometries | 🔴 High | ✅ DONE | 30 min |

**Success criteria:** ~50,000 detections loaded into fire_detections

### 2.2 Event clustering
| # | Task | Subtask | Priority | Status | Estimate |
|---|------|---------|----------|--------|----------|
| 2.2.1 | Implement DBSCAN | eps=500m, min_samples=3 | 🔴 High | ✅ DONE | 2h |
| 2.2.2 | Create fire_events | From clusters | 🔴 High | ✅ DONE | 1h |
| 2.2.3 | Calculate statistics | avg_frp, duration, area | 🔴 High | ✅ DONE | 1h |
| 2.2.4 | Assign province | Basic reverse geocoding | 🟡 Medium | ⏳ PENDING | 45 min |
| 2.2.5 | Clustering tests | Validate spatial separation | 🔴 High | 🔜 PENDING | 1h |

**Success criteria:** ~5,000 fire_events created with statistics

### 2.3 Protected areas
| # | Task | Subtask | Priority | Status | Estimate |
|---|------|---------|----------|--------|----------|
| 2.3.1 | Download shapefiles | datos.gob.ar (APN) | 🔴 High | 🔜 PENDING | 30 min |
| 2.3.2 | Simplify geometries | ST_Simplify(100m) | 🔴 High | 🔜 PENDING | 45 min |
| 2.3.3 | Load protected_areas | With correct categories | 🔴 High | 🔜 PENDING | 1h |
| 2.3.4 | Calculate intersections | fire_protected_area_intersections | 🔴 High | 🔜 PENDING | 1.5h |
| 2.3.5 | Calculate prohibition_until | fire_date + 60 years | 🔴 High | 🔜 PENDING | 30 min |

**Success criteria:** ~400 protected areas loaded, intersections calculated

---

## 📋 PHASE 3: API core (week 3-4)

### 3.1 SQLAlchemy models
| # | Task | Subtask | Priority | Status | Estimate |
|---|------|---------|----------|--------|----------|
| 3.1.1 | FireDetection model | With Geography | 🔴 High | ⏳ PENDING | 45 min |
| 3.1.2 | FireEvent model | With relationships | 🔴 High | ⏳ PENDING | 45 min |
| 3.1.3 | ProtectedArea model | With GIST index | 🔴 High | 🔜 PENDING | 45 min |
| 3.1.4 | Remaining models | 11 additional tables | 🔴 High | 🔜 PENDING | 2h |
| 3.1.5 | Relationships | FKs, back_populates | 🔴 High | 🔜 PENDING | 1h |

### 3.2 Pydantic schemas
| # | Task | Subtask | Priority | Status | Estimate |
|---|------|---------|----------|--------|----------|
| 3.2.1 | FireEventResponse | For GET /fires | 🔴 High | ⏳ PENDING | 30 min |
| 3.2.2 | AuditRequest/Response | For UC-01 | 🔴 High | ✅ DONE | 45 min |
| 3.2.3 | CertificateRequest/Response | For UC-07 | 🔴 High | ✅ DONE | 45 min |
| 3.2.4 | CitizenReportRequest | For UC-09 | 🟡 Medium | 🔜 PENDING | 30 min |
| 3.2.5 | HistoricalReportRequest | For UC-11 | 🟡 Medium | 🔜 PENDING | 30 min |
| 3.2.6 | Custom validators | Lat/lon, dates | 🔴 High | ⏳ PENDING | 30 min |

### 3.3 REST Endpoints
| # | Task | Subtask | Priority | Status | Estimate |
|---|------|---------|----------|--------|----------|
| 3.3.1 | GET /health | Full health check (DB, Redis, GEE, R2) | 🔴 High | ✅ DONE | 15 min |
| 3.3.2 | GET /fires | Paginated list | 🔴 High | ✅ DONE | 1h |
| 3.3.3 | GET /fires/{id} | Detail with evidence | 🔴 High | ✅ DONE | 45 min |
| 3.3.4 | **POST /audit/land-use** | **UC-01 core** | 🔴 High | ✅ DONE | 2h |
| 3.3.5 | **POST /certificates/request** | **UC-07 core** | 🔴 High | ✅ DONE | 2h |
| 3.3.6 | GET /certificates/verify/{number} | Public verification | 🔴 High | ⏳ PENDING | 1h |
| 3.3.7 | POST /citizen/report | UC-09 | 🟡 Medium | 🔜 PENDING | 1.5h |
| 3.3.8 | GET /quality/{fire_id} | UC-10 (renumbered) | 🟡 Medium | 🔜 PENDING | 1h |
| 3.3.9 | POST /reports/historical-fire | UC-11 (renumbered) | 🟡 Medium | 🔜 PENDING | 2h |
| 3.3.10 | POST /reports/judicial | UC-02 | 🟡 Medium | 🔜 PENDING | 2h |
| 3.3.11 | GET /monitoring/recovery | UC-06 | 🟡 Medium | 🔜 PENDING | 1.5h |

**Success criteria:** All endpoints respond < 2 seconds

### 3.4 Services (business logic)
| # | Task | Subtask | Priority | Status | Estimate |
|---|------|---------|----------|--------|----------|
| 3.4.1 | SpatialService | PostGIS Queries | 🔴 High | ✅ DONE | 2h |
| 3.4.2 | AuditService | UC-01 logic | 🔴 High | ✅ DONE | 2h |
| 3.4.3 | CertificateService | PDF + QR + hash | 🔴 High | ✅ DONE | 3h |
| 3.4.4 | PDFComposerService | Jinja2/WeasyPrint templates | 🟡 Medium | ⏳ PENDING | 2h |
| 3.4.5 | ClimateService | Open-Meteo wrapper | 🟡 Medium | 🔜 PENDING | 1.5h |
| 3.4.6 | GEEService | Google Earth Engine wrapper | 🔴 High | ✅ DONE | 3h |
| 3.4.7 | **VAEService** | **Vegetation Analysis Engine** | 🔴 High | 🔜 PENDING | 4h |
| 3.4.8 | **ERSService** | **Evidence Reporting Service** | 🔴 High | 🔜 PENDING | 3h |
| 3.4.9 | FIRMSService | NASA FIRMS wrapper | 🔴 High | ✅ DONE | 1.5h |

---

## 📋 PHASE 4: Async workers (week 4-5)

### 4.1 Celery configuration
| # | Task | Subtask | Priority | Status | Estimate |
|---|------|---------|----------|--------|----------|
| 4.1.1 | celery_app.py | Redis Broker | 🔴 High | ✅ DONE | 30 min |
| 4.1.2 | Celery Beat | Task scheduler | 🟡 Medium | 🔜 PENDING | 30 min |
| 4.1.3 | Result backend | Redis/PostgreSQL | 🟡 Medium | ⏳ PENDING | 30 min |
| 4.1.4 | Queue configuration | recovery_queue, destruction_queue | 🔴 High | 🔜 PENDING | 30 min |
| 4.1.5 | Retry policies | Exponential backoff (3 retries) | 🔴 High | 🔜 PENDING | 45 min |

### 4.2 Tasks
| # | Task | Subtask | Priority | Status | Estimate |
|---|------|---------|----------|--------|----------|
| 4.2.1 | download_firms_daily | Automatic download | 🔴 High | ✅ DONE | 1.5h |
| 4.2.2 | cluster_new_detections | Daily clustering | 🔴 High | ✅ DONE | 1h |
| 4.2.3 | enrich_with_climate | Open-Meteo batch | 🟡 Medium | 🔜 PENDING | 2h |
| 4.2.4 | download_sentinel_imagery | GEE integration | 🟡 Medium | ⏳ PENDING | 3h |
| 4.2.5 | **check_reforestation (VAE)** | **NDVI recovery - UC-06** |  High | 🔜 PENDING | 2.5h |
| 4.2.6 | **detect_land_use_changes (VAE)** | **Illegal use - UC-08** |  High | 🔜 PENDING | 2.5h |
| 4.2.7 | generate_evidence_package (ERS) | ZIP for reports (UC-09) |  Medium | 🔜 PENDING | 2h |
| 4.2.8 | generate_historical_report (ERS) | Historical PDFs (UC-11) | 🟡 Medium | 🔜 PENDING | 2h |

---

## 📋 PHASE 5: React frontend (week 5-6)

### 5.1 Setup & configuration
| # | Task | Subtask | Priority | Status | Estimate |
|---|------|---------|----------|--------|----------|
| 5.1.1 | Create Vite project | React + TypeScript | 🔴 High | 🔜 PENDING | 15 min |
| 5.1.2 | Tailwind CSS | Configuration | 🔴 High | 🔜 PENDING | 20 min |
| 5.1.3 | Theme (branding) | Colors, fonts | 🔴 High | 🔜 PENDING | 30 min |
| 5.1.4 | React Router | Main routes | 🔴 High | 🔜 PENDING | 30 min |
| 5.1.5 | Axios/TanStack Query | API client | 🔴 High | 🔜 PENDING | 30 min |

### 5.2 Core components
| # | Task | Subtask | Priority | Status | Estimate |
|---|------|---------|----------|--------|----------|
| 5.2.1 | Layout/Navbar | Instagram style | 🔴 High | 🔜 PENDING | 2h |
| 5.2.2 | MapComponent | Leaflet + markers | 🔴 High | 🔜 PENDING | 3h |
| 5.2.3 | FireCard | Fire card | 🔴 High | 🔜 PENDING | 1.5h |
| 5.2.4 | StatusBadge | Legal statuses | 🔴 High | 🔜 PENDING | 30 min |
| 5.2.5 | SearchForm | Search by coords | 🔴 High | 🔜 PENDING | 1h |

### 5.3 Pages
| # | Task | Subtask | Priority | Status | Estimate |
|---|------|---------|----------|--------|----------|
| 5.3.1 | Home/Feed | Recent fires (IG style) | 🔴 High | 🔜 PENDING | 3h |
| 5.3.2 | MapView | Fullscreen map | 🔴 High | 🔜 PENDING | 2h |
| 5.3.3 | AuditPage | Form UC-01 | 🔴 High | 🔜 PENDING | 2h |
| 5.3.4 | CertificatePage | Request UC-07 | 🔴 High | 🔜 PENDING | 2h |
| 5.3.5 | ReportPage | Report UC-09 | 🟡 Medium | 🔜 PENDING | 2h |
| 5.3.6 | FireDetail | Full detail | 🟡 Medium | 🔜 PENDING | 2h |
| 5.3.7 | VerifyPage | Verify certificate | 🟡 Medium | 🔜 PENDING | 1h |
| 5.3.8 | HistoricalReportsPage | UC-11 request | 🟡 Medium | 🔜 PENDING | 2h |
| 5.3.9 | DataQualityPage | UC-10 metrics | 🟢 Low | 🔜 PENDING | 1.5h |

### 5.4 UI/UX features (Instagram style)
| # | Task | Subtask | Priority | Status | Estimate |
|---|------|---------|----------|--------|----------|
| 5.4.1 | Fire stories | Horizontal carousel | 🟡 Medium | 🔜 PENDING | 2h |
| 5.4.2 | Infinite feed | Infinite scroll | 🟡 Medium | 🔜 PENDING | 1.5h |
| 5.4.3 | Like/Save fires | Local favorites | 🟢 Low | 🔜 PENDING | 1h |
| 5.4.4 | Share modal | Share on social media | 🟢 Low | 🔜 PENDING | 1h |
| 5.4.5 | Dark mode | Theme toggle | 🟢 Low | 🔜 PENDING | 1h |
| 5.4.6 | Animations | Framer Motion | 🟢 Low | 🔜 PENDING | 2h |

---

## 📋 PHASE 6: Testing & deploy (week 6)

### 6.1 Testing
| # | Task | Subtask | Priority | Status | Estimate |
|---|------|---------|----------|--------|----------|
| 6.1.1 | Unit tests models | pytest | 🔴 High | 🔜 PENDING | 2h |
| 6.1.2 | Unit tests services | pytest + mock | 🔴 High | 🔜 PENDING | 3h |
| 6.1.3 | Integration tests API | pytest + TestClient | 🔴 High | 🔜 PENDING | 3h |
| 6.1.4 | E2E test audit flow | Full UC-01 | 🔴 High | 🔜 PENDING | 2h |
| 6.1.5 | Coverage > 80% | pytest-cov | 🟡 Medium | 🔜 PENDING | 1h |

### 6.2 Deploy
| # | Task | Subtask | Priority | Status | Estimate |
|---|------|---------|----------|--------|----------|
| 6.2.1 | Configure Cloudflare R2 | Bucket + CORS | 🔴 High | ✅ DONE | 30 min |
| 6.2.2 | Deploy API (Oracle Cloud) | VM + Nginx + SSL | 🔴 High | ✅ DONE | 2h |
| 6.2.3 | Configure DNS | FreeDynamicDNS | 🔴 High | ✅ DONE | 30 min |
| 6.2.4 | SSL/HTTPS | Let's Encrypt Certbot | 🔴 High | ✅ DONE | 1h |
| 6.2.5 | GitHub Actions CI/CD | Lint + test + deploy | 🟡 Medium | 🔜 PENDING | 2h |
| 6.2.6 | Secrets Management | GEE credentials, API keys | 🔴 High | ✅ DONE | 30 min |
| 6.2.7 | Production monitoring | UptimeRobot, logs | 🟡 Medium | 🔜 PENDING | 1h |

---

## 📋 PHASE 7: Architecture & validation (completed ✅)

### 7.1 Architectural validation
| # | Task | Subtask | Priority | Status | Estimate |
|---|------|---------|----------|--------|----------|
| 7.1.1 | Cross-validation architecture | Docs vs implementation | 🔴 High | ✅ DONE | 2h |
| 7.1.2 | Use case review | UC-01 to UC-11 | 🔴 High | ✅ DONE | 1h |
| 7.1.3 | DB schema validation | 14 tables, indexes, triggers | 🔴 High | ✅ DONE | 1.5h |
| 7.1.4 | Overlap identification | VAE, ERS modules | 🔴 High | ✅ DONE | 1.5h |
| 7.1.5 | Validation report | 16 findings documented | 🔴 High | ✅ DONE | 1h |

### 7.2 Critical corrections
| # | Task | Subtask | Priority | Status | Estimate |
|---|------|---------|----------|--------|----------|
| 7.2.1 | Renumber UC-11 → UC-10 | Data Quality | 🔴 High | ✅ DONE | 30 min |
| 7.2.2 | Renumber UC-12 → UC-11 | Historical Reports | 🔴 High | ✅ DONE | 30 min |
| 7.2.3 | Add RLS policy | historical_report_requests | 🔴 High | ✅ DONE | 15 min |
| 7.2.4 | Update summary | 10 → 11 use cases | 🔴 High | ✅ DONE | 5 min |
| 7.2.5 | Restore clustering.py | Worker consistency | 🔴 High | ✅ DONE | 10 min |
| 7.2.6 | Add historical.py endpoint | Routes documented | 🔴 High | ✅ DONE | 10 min |

### 7.3 Operational improvements
| # | Task | Subtask | Priority | Status | Estimate |
|---|------|---------|----------|--------|----------|
| 7.3.1 | Error handling strategy | Retry, DLQ, alerting | 🔴 High | ✅ DONE | 1.5h |
| 7.3.2 | Security hardening | GEE credentials, rate limiting | 🔴 High | ✅ DONE | 1h |
| 7.3.3 | Monitoring & observability | Prometheus, logs, tracing | 🔴 High | ✅ DONE | 1.5h |
| 7.3.4 | GEE rate limits | Precise documentation | 🔴 High | ✅ DONE | 30 min |
| 7.3.5 | Health checks | Critical components | 🔴 High | ✅ DONE | 45 min |
| 7.3.6 | API versioning | Deprecation strategy | 🔴 High | ✅ DONE | 45 min |
| 7.3.7 | Performance indexes | Composite indexes | 🔴 High | ✅ DONE | 1h |
| 7.3.8 | Data validation | SQL Triggers | 🔴 High | ✅ DONE | 1h |
| 7.3.9 | Retention policies | Legal compliance | 🔴 High | ✅ DONE | 45 min |
| 7.3.10 | VAE queue separation | recovery vs destruction | 🔴 High | ✅ DONE | 30 min |
| 7.3.11 | ERS service docs | Methods and location | 🔴 High | ✅ DONE | 30 min |

---

## 📊 Estimates summary

| Phase | Tasks | Est. Hours | Week | Status |
|-------|-------|------------|------|--------|
| 1. Infrastructure | 15 | 8h | 1 | ✅ 90% DONE |
| 2. Data Ingestion | 15 | 14h | 2 | ✅ 80% DONE |
| 3. API Core | 27 | 32h | 3-4 | ⏳ 50% DONE |
| 4. Workers | 13 | 16h | 4-5 | ⏳ 40% DONE |
| 5. Frontend | 24 | 34h | 5-6 | 🔜 0% DONE |
| 6. Testing/Deploy | 13 | 19h | 6 | ✅ 90% DONE |
| 7. Architecture/Validation | 22 | 16h | - | ✅ 100% DONE |
| **TOTAL** | **133** | **144h** | **6 weeks** | **~75% completed** |

---

## 🎯 Immediate next steps (prioritized)

### 🔥 High priority (this week)
```
1. ✅ DONE: Full architectural validation
   └── ✅ Validation report with 16 findings
   └── ✅ Critical corrections applied
   └── ✅ Operational improvements implemented

2. ✅ DONE: Production deploy (Oracle Cloud)
   └── ✅ VM configured (Ampere A1, 1 OCPU, 6GB RAM)
   └── ✅ Nginx + SSL (Let's Encrypt)
   └── ✅ DNS (forestguard.freedynamicdns.org)
   └── ✅ API Live: https://forestguard.freedynamicdns.org/docs

2. ⏳ IN PROGRESS: Implement VAE Service
   └── 🔜 vae_service.py with core methods
   └── 🔜 fetch_ndvi_monthly(fire_event_id, date)
   └── 🔜 detect_anomalies(ndvi_values)

3. ⏳ IN PROGRESS: Implement ERS Service
   └── 🔜 ers_service.py with core methods
   └── 🔜 aggregate_evidence(fire_event_id, date_range)
   └── 🔜 generate_pdf(evidence, template)
   └── 🔜 create_verification_hash(pdf_bytes)

4. 🔜 PENDING: Complete missing endpoints
   └── 🔜 POST /reports/judicial (UC-02)
   └── 🔜 POST /reports/historical-fire (UC-11)
   └── 🔜 GET /monitoring/recovery (UC-06)
   └── 🔜 POST /citizen/report (UC-09)
```

### 🟡 Medium priority (next 2 weeks)
```
5. 🔜 Load protected areas data
   └── Download official shapefiles
   └── Load ~400 protected areas
   └── Calculate intersections with fire_events

6. 🔜 Implement VAE workers
   └── check_reforestation.py (UC-06)
   └── detect_land_use_changes.py (UC-08)
   └── Configure separate queues

7. 🔜 Unit and integration tests
   └── Coverage > 80%
   └── E2E flows for UC-01, UC-07
```

### 🟢 Low priority (next month)
```
8. 🔜 React Frontend (Vite + Tailwind)
   └── Initial setup
   └── Core components
   └── Main pages

9. 🔜 Production deploy parts
   └── Cloudflare R2
   └── Railway/Fly.io API
   └── Vercel Frontend
```

---

## 📈 Progress metrics

### Recently completed
- ✅ SQL Schema v0.2 with 14 tables
- ✅ Use cases UC-01 to UC-11 documented
- ✅ Unified architecture (VAE + ERS)
- ✅ Architectural validation (16 findings resolved)
- ✅ Operational improvements (monitoring, security, error handling)
- ✅ 5 critical corrections applied
- ✅ 11 operational improvements implemented

### In development
- ⏳ VAE and ERS services
- ⏳ Endpoints UC-02, UC-06, UC-09, UC-11
- ⏳ Celery Workers for VAE

### Blockers
- ⚠️ None identified currently

---

## 📞 Contact

**Author:** Nicolás Gabriel Hruszczak  
**Role:** Business Analyst / Developer  
**Project:** ForestGuard - REST API Portfolio

---

*Last update: 2026-01-28*  
*Plan version: 2.0*  
*Main changes: UC-10/11 renumbering, Phase 7 (Validation) addition, status update 70%*
