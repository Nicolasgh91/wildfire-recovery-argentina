# ForestGuard — Documentation Index

Master index of canonical documentation. Last updated: 2026-02-18.

## 📁 Estructura de Documentación

```
docs/
├── frontend/          # Documentación del frontend
├── backend/           # Documentación del backend y API
├── infrastructure/    # Deployment, producción y operaciones
├── security/          # Auditorías y políticas de seguridad
├── architecture/      # Diseño y deuda técnica
├── development/       # Scripts, mantenimiento y runbooks
└── project/           # Reviews y gestión de episodios
```

## Getting Started

| Document | Path | Description |
|----------|------|-------------|
| **README** | [`README.md`](../README.md) | Project overview, setup, API reference |
| **Frontend README** | [`frontend/README.md`](frontend/README.md) | Frontend routes, contracts, feature flags |

## 🏗️ Architecture & Design

| Document | Path | Description |
|----------|------|-------------|
| **Production Roadmap** | [`architecture/design/roadmap_prod.md`](architecture/design/roadmap_prod.md) | MVP/post-MVP phases, use case status |
| **Technical Tasks** | [`architecture/design/technical_tasks_roadmap.md`](architecture/design/technical_tasks_roadmap.md) | Detailed technical tasks, naming conventions |
| **Workers Documentation** | [`backend/workers/workers_documentation.md`](backend/workers/workers_documentation.md) | Celery tasks, queues, monitoring |
| **Clustering Analysis** | [`architecture/design/clustering_analysis.md`](architecture/design/clustering_analysis.md) | Fire detection clustering methodology |
| **Technical Debt** | [`architecture/technical-debt/technical_tasks.md`](architecture/technical-debt/technical_tasks.md) | Refactoring and technical debt tasks |

## 🔐 Auth & Login

| Document | Path | Description |
|----------|------|-------------|
| **ADR: Supabase Auth** | [`adr/ADR-0001-auth-supabase.md`](adr/ADR-0001-auth-supabase.md) | Architecture decision record for auth |
| **Auth Matrix** | [`backend/api/auth_matrix.md`](backend/api/auth_matrix.md) | Endpoint → auth requirements table (BL-012) |

## 🚀 Infrastructure & Deployment

| Document | Path | Description |
|----------|------|-------------|
| **Deployment Guide** | [`infrastructure/deployment/DEPLOYMENT.md`](infrastructure/deployment/DEPLOYMENT.md) | Production deployment guide |
| **VM Deployment Commands** | [`infrastructure/deployment/vm-deployment-commands.md`](infrastructure/deployment/vm-deployment-commands.md) | VM setup commands |
| **Quick Deployment** | [`infrastructure/deployment/quick-deployment-commands.md`](infrastructure/deployment/quick-deployment-commands.md) | Fast deployment commands |
| **Quick Fixes** | [`infrastructure/deployment/quick-fixes.md`](infrastructure/deployment/quick-fixes.md) | Common deployment fixes |
| **Immediate Fix** | [`infrastructure/deployment/immediate-fix.md`](infrastructure/deployment/immediate-fix.md) | Emergency fixes |
| **Production Analysis** | [`infrastructure/production/vm-production-analysis.md`](infrastructure/production/vm-production-analysis.md) | Production VM analysis |
| **Production Cleanup** | [`infrastructure/production/PRODUCTION_CLEANUP_SUMMARY.md`](infrastructure/production/PRODUCTION_CLEANUP_SUMMARY.md) | Cleanup procedures |
| **File Pruning Report** | [`infrastructure/ops/prod_file_pruning_report.md`](infrastructure/ops/prod_file_pruning_report.md) | File management report |

## 🔒 Security

| Document | Path | Description |
|----------|------|-------------|
| **Security Audit** | [`security/audits/security_audit.md`](security/audits/security_audit.md) | Security findings (SEC-001→SEC-013) |
| **Security Improvements** | [`security/audits/SECURITY_IMPROVEMENTS_SUMMARY.md`](security/audits/SECURITY_IMPROVEMENTS_SUMMARY.md) | Security improvements summary |
| **Deep Security Audit** | [`security/audits/security_deep_audit_2026-02-16.md`](security/audits/security_deep_audit_2026-02-16.md) | Comprehensive security audit |
| **Security Audit Final** | [`security/audits/security_audit_final.md`](security/audits/security_audit_final.md) | Final security audit |
| **Technical Debt (Security)** | [`security/audits/technical_debt.md`](security/audits/technical_debt.md) | Security technical debt |
| **Security Audit Codex** | [`security/audits/security_audit_codex_plan.md`](security/audits/security_audit_codex_plan.md) | Security audit plan |
| **CSP Deployment** | [`security/policies/CSP_DEPLOYMENT.md`](security/policies/CSP_DEPLOYMENT.md) | Content Security Policy |
| **OCSP Stapling** | [`security/policies/OCSP_STAPLING.md`](security/policies/OCSP_STAPLING.md) | Certificate stapling |
| **Dependabot** | [`security/policies/DEPENDABOT.md`](security/policies/DEPENDABOT.md) | Dependency management |
| **Secrets Management** | [`security/policies/secrets-README.md`](security/policies/secrets-README.md) | Secrets handling guide |

## 🛠️ Development & Runbooks

| Document | Path | Description |
|----------|------|-------------|
| **JWT Local Setup** | [`development/runbooks/auth-jwt-local.md`](development/runbooks/auth-jwt-local.md) | Local JWT testing setup |
| **Auth Validation** | [`development/runbooks/auth-validation.md`](development/runbooks/auth-validation.md) | Auth validation procedures |
| **Carousel Manual Run** | [`development/runbooks/carousel_manual_run.md`](development/runbooks/carousel_manual_run.md) | Manual carousel procedures |
| **Scripts Documentation** | [`development/scripts/scripts_readme.md`](development/scripts/scripts_readme.md) | Scripts overview |
| **Maintenance Guide** | [`development/maintenance/README.md`](development/maintenance/README.md) | Maintenance procedures |

## 🎨 Frontend

| Document | Path | Description |
|----------|------|-------------|
| **Routing Access Matrix (RUC)** | [`frontend/routing_access_ruc.md`](frontend/routing_access_ruc.md) | Route access rules for guest/authenticated users |
| **RUC Execution Log** | [`frontend/ruc_home_landing_execution_log.md`](frontend/ruc_home_landing_execution_log.md) | Task-by-task implementation and validation log |
| **Frontend Technical Debt** | [`frontend/technical_debt.md`](frontend/technical_debt.md) | Open frontend debt and follow-up actions |
| **Frontend Build Audit** | [`frontend/build/frontend_build_audit.md`](frontend/build/frontend_build_audit.md) | Build process audit |
| **Playwright Test Reports** | [`frontend/testing/`](frontend/testing/) | Automated test reports |

## 📊 Project Management & Reviews

| Document | Path | Description |
|----------|------|-------------|
| **Documentation Audit** | [`project/reviews/documentation_audit.md`](project/reviews/documentation_audit.md) | Doc consistency findings |
| **Performance Audit** | [`project/reviews/performance_audit.md`](project/reviews/performance_audit.md) | Performance findings (PERF-001→PERF-011) |
| **i18n UI Matrix** | [`project/reviews/i18n_ui_matrix_remaining.md`](project/reviews/i18n_ui_matrix_remaining.md) | Internationalization matrix |
| **i18n DoD Final** | [`project/reviews/i18n_dod_final.md`](project/reviews/i18n_dod_final.md) | i18n definition of done |
| **Fixes Applied** | [`project/reviews/fixes_applied.md`](project/reviews/fixes_applied.md) | Applied fixes summary |
| **Backlog Recommendations** | [`project/reviews/backlog_recommendations.md`](project/reviews/backlog_recommendations.md) | Backlog prioritization |
| **Episode Technical Debt** | [`project/episodes/technical_debt.md`](project/episodes/technical_debt.md) | Episode-related debt |
| **Task Execution Log** | [`project/episodes/task_execution_log.md`](project/episodes/task_execution_log.md) | Task execution tracking |
| **Episode Flow Plan** | [`project/episodes/plan_episode_flow.md`](project/episodes/plan_episode_flow.md) | Episode workflow plan |
| **Tech Tasks Final** | [`project/episodes/1_tech_tasks_final.md`](project/episodes/1_tech_tasks_final.md) | Final technical tasks |
