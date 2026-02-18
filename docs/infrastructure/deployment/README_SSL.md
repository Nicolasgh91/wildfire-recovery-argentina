# SSL Certificate Setup - Docker Mode

This repository uses Docker-based Certbot as the official SSL workflow.

## Official Documentation

Use `docs/SSL_SETUP.md` as the single source of truth.

## Current Operating Model

- Certificate issuance: one-shot Certbot command in Docker profile `ssl`.
- Renewal: host scheduler (cron/systemd) runs `scripts/renew-ssl-cron.sh`.
- Nginx reload is mandatory after renewal.
- No long-running Certbot renewal loop container.

## Quick Commands

```bash
# Initial issuance
./scripts/setup-ssl.sh

# Manual renewal
./scripts/renew-ssl.sh

# Dry-run renewal
./scripts/renew-ssl.sh --dry-run

# Verify status
./scripts/verify-ssl.sh

# Certbot certificates
docker compose --profile ssl run --rm certbot certificates
```
