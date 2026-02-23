Context
The deploy workflow (deploy-prod-vm.yml) fails because the Docker daemon is unresponsive, but no diagnostics are captured at the point of failure. Additionally, most containers report as unhealthy even when they are operational, due to incorrect healthcheck configurations in docker-compose.yml:

celery-beat uses celery inspect ping which only checks workers, not the beat scheduler
flower uses curl but the worker image (Dockerfile.worker) doesn't install curl
nginx uses curl but nginx:alpine doesn't include curl
All workers use celery inspect ping which broadcasts to ALL workers via the broker, causing simultaneous false negatives under load

Changes
1. Enhanced Docker daemon diagnostics on failure
File: .github/workflows/deploy-prod-vm.yml (lines 105-109)
When docker info fails, collect diagnostics before exit 1:

id, groups — user/group context
systemctl is-active docker, systemctl status docker --no-pager -l — daemon status
journalctl -u docker -n 200 --no-pager — daemon logs
systemctl status containerd --no-pager -l, journalctl -u containerd -n 200 --no-pager — containerd status
df -h, df -i, free -m — disk/inode/memory
Each command wrapped with timeout and || true to prevent hangs
Use === DIAGNOSTIC: ... === markers for log scanning

2. Fix celery-beat healthcheck
File: docker-compose.yml (line 340)
Replace celery inspect ping with process-level check:
yamltest: ["CMD-SHELL", "pgrep -f 'celery.*beat' || exit 1"]
Beat is a scheduler, not a worker — it doesn't respond to inspect ping.
3. Fix flower and nginx healthchecks (missing curl)
File: docker-compose.yml
flower (line 366) — use Python stdlib (available in python:3.11-slim):
yamltest: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:5555/healthcheck')\" || exit 1"]
nginx (line 417) — use wget (available in Alpine by default):
yamltest: ["CMD-SHELL", "wget --spider -q http://localhost/nginx-health || exit 1"]
4. Fix worker healthchecks (all 4 workers)
File: docker-compose.yml (lines 143, 198, 253, 309)
Replace celery inspect ping ... | grep -q OK with process-level liveness for worker-ingestion, worker-clustering, worker-analysis, worker-reports:
yamltest: ["CMD-SHELL", "pgrep -f 'celery.*worker' || exit 1"]
This avoids broker-dependent broadcast pings that cause cascading false negatives.
5. Automated tests for healthcheck contracts
New file: tests/unit/test_compose_healthchecks.py
Static tests that parse docker-compose.yml (via PyYAML) and verify:

celery-beat does NOT use celery inspect ping
flower does NOT use curl
nginx does NOT use curl
All workers use process-level checks, not inspect ping
All critical services define a healthcheck

CI integration: Add compose-contracts job to .github/workflows/security.yml — only needs pytest + pyyaml, runs in seconds.
Files to Modify
FileActiondocker-compose.ymlEdit 7 healthcheck definitions.github/workflows/deploy-prod-vm.ymlExpand Docker daemon failure diagnostics.github/workflows/security.ymlAdd compose-contracts CI jobtests/unit/test_compose_healthchecks.pyCreate new test module
Verification

Run pytest tests/unit/test_compose_healthchecks.py -v — all tests pass against the updated compose file
Run docker compose config — validates compose YAML syntax
Visually inspect the workflow YAML for correct indentation/structure