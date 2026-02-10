# ForestGuard Service Level Objectives (SLOs)

## Overview

This document defines the Service Level Objectives for the ForestGuard API.
SLOs are measurable targets that define the level of service we commit to providing.

## Availability SLOs

| Service | Target | Measurement |
|---------|--------|-------------|
| **API Overall** | 99.5% | Monthly uptime |
| **Health Endpoints** | 99.9% | `/health/live`, `/health/ready` |
| **Payment Webhooks** | 99.9% | Critical path - must not lose payments |

## Latency SLOs

| Endpoint Category | P50 | P95 | P99 |
|-------------------|-----|-----|-----|
| **Health checks** | 50ms | 100ms | 200ms |
| **Fire listings** | 200ms | 400ms | 800ms |
| **Fire details** | 100ms | 200ms | 400ms |
| **Land-use audit** | 500ms | 1.5s | 3s |
| **Report generation** | Async | Async | Async |
| **Payment checkout** | 300ms | 800ms | 1.5s |

## Error Rate SLOs

| Category | Target | Timeframe |
|----------|--------|-----------|
| **5xx errors** | < 0.1% | Rolling 24h |
| **4xx errors** | < 5% | Rolling 24h |
| **Webhook failures** | < 0.01% | Rolling 7 days |

## Capacity SLOs

| Metric | Threshold | Action |
|--------|-----------|--------|
| **API requests/sec** | 100 | Scale horizontally |
| **Database connections** | 80% pool | Alert + investigate |
| **Redis memory** | 80% | Purge expired keys |
| **Worker queue depth** | 1000 tasks | Scale workers |

## Recovery SLOs

| Scenario | RTO (Recovery Time) | RPO (Recovery Point) |
|----------|---------------------|---------------------|
| **API failure** | 5 minutes | N/A (stateless) |
| **Database failure** | 15 minutes | 1 hour |
| **Worker failure** | 10 minutes | Tasks requeued |
| **Full DR** | 4 hours | 24 hours |

## Monitoring Configuration

### Prometheus Metrics

```yaml
# SLO-related metrics to collect
- forestguard_http_request_duration_seconds
- forestguard_http_requests_total
- forestguard_http_errors_total
- forestguard_database_query_duration_seconds
- forestguard_celery_task_duration_seconds
- forestguard_celery_queue_length
```

### Alert Rules

```yaml
groups:
  - name: slo_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(forestguard_http_errors_total{status=~"5.."}[5m]) / rate(forestguard_http_requests_total[5m]) > 0.001
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Error rate above SLO threshold"
          
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(forestguard_http_request_duration_seconds_bucket[5m])) > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "P95 latency above SLO threshold"
          
      - alert: LowAvailability
        expr: up{job="forestguard-api"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "ForestGuard API is down"
```

## SLO Budget Tracking

### Error Budget Calculation

```
Monthly Error Budget = 100% - SLO Target
Example for 99.5% availability:
- Budget = 0.5% = 3.6 hours/month downtime allowed
- Weekly budget = ~54 minutes
- Daily budget = ~7.2 minutes
```

### Budget Consumption Dashboard

Track these metrics in Grafana:
1. Error budget remaining (%)
2. Burn rate (budget consumption speed)
3. Time until budget exhaustion
4. Historical SLO compliance

## Review Schedule

| Review Type | Frequency | Participants |
|-------------|-----------|--------------|
| **SLO Check** | Weekly | On-call engineer |
| **SLO Tuning** | Monthly | Engineering team |
| **SLO Revision** | Quarterly | Product + Engineering |

---

*Last Updated: 2026-02-08*
*Version: 1.0.0*
