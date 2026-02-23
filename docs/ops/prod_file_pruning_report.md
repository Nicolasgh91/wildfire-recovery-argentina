# Production Environment Storage Optimization Report

**Goal**: Analyze the repository sizes and determine which files and directories can be excluded to optimize disk usage in the production virtual machine (VM).

## 1. Repository Size Breakdown

A complete scan of the repository directory reveals the following sizes (sorted by largest, calculated locally):

| Directory | Size (MB) | Purpose |
| :--- | :--- | :--- |
| `.venv` / `venv` | ~1.1 GB | Python virtual environments with downloaded packages. |
| `frontend/node_modules` | 350.22 | Node dependencies for the frontend. |
| `data` | 179.95 | Raw, seed, or temporary geospatial data. |
| `.mypy_cache` | 65.28 | Cache for static type checking. |
| `temp_files` | 61.37 | Temporary files generated during processes. |
| `logs` | 21.16 | Application and system logs. |

*Note: The core tracked files (source code, configuration, images) amount to less than 50 MB in total inside the `.git` tracking system.*

## 2. Production Environment (VM) Execution Context

Based on the `deploy-prod-vm.yml` and `docker-compose.yml`, the production environment operates as follows:
- The entire repository is fetched via `git pull --ff-only origin main`.
- The application runs via **Docker Compose**:
  - The API and Workers are built using Docker (`Dockerfile.api`, `Dockerfile.worker`).
  - The Frontend is pulled as a pre-built image from GitHub Container Registry (`ghcr.io/.../frontend:latest`).
  - Nginx, Redis, and Certbot use pre-built Alpine/standard images.

This means **most of the local development directories are NOT needed on the production VM** for runtime.

## 3. Recommended Exclusions

The following directories/files consume the most space and **must be excluded** from the production VM context. 

### To Exclude from Docker Builds (`.dockerignore`)
The `.dockerignore` file in the root is already well-configured to exclude these files, preventing them from being baked into the Docker images. Ensure the following rules remain intact:
- `.venv` / `venv` / `env`
- `frontend/` (Frontend source code is NOT needed because the API container only needs the backend code, and the frontend is a separate pre-built image).
- `**/*/node_modules/`
- `data/`
- `.mypy_cache/`
- `temp_files/`
- `tests/`
- `docs/`

### To Exclude from VM Host Copying
Since the repo is pulled directly via Git on the VM, the tracked source code takes very little space (~42 MB). Un-tracked folders (like `.venv`, `node_modules`, `data`) will **not** exist on the VM unless they are manually generated there by running `npm install` or `python -m venv` on the host outside of Docker.

**Rule of Thumb:**
Do *not* run local development commands (like `pip install -r requirements.txt` or `npm install`) on the VM host. Rely purely on Docker to isolate dependencies. By doing this, `.venv` and `node_modules` will only exist inside the Docker images (which are optimized via their respective Dockerfiles) and not on the VM host disk.

## 4. Why Disk Space gets Full on the VM

Since the repository source code is incredibly small, the real culprits for disk space exhaustion on the VM are usually:
1. **Dangling Docker Images**: Previous image builds that are no longer tagged.
2. **BuildKit Cache**: Docker's internal cache for building images (which can grow to several GBs).
3. **Old, stopped containers**.

### Automated Solutions Implemented
The `deploy-prod-vm.yml` workflow *already* contains steps to handle this:
```bash
docker builder prune -af --filter "until=168h"
docker image prune -af --filter "until=168h"
```
These commands automatically aggressively clean up Docker images and caches older than 7 days, preventing the VM from filling up over time.

## Conclusion

The current architecture is highly optimized for deployment:
1. The `.dockerignore` file perfectly isolates heavy local folders from image builds.
2. The Git `.gitignore` prevents heavy folders from being tracked and pushed to the VM.
3. The deployment script leverages Docker pruning.

No immediate manual file deletions from the tracked repository are required to save space, but it is critical to ensure `docker-compose.override.yml` is never present/active in production (as enforced by `deploy-prod-vm.yml`), as this would trigger unnecessary local builds.
