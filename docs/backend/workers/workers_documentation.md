# ForestGuard Worker Tasks Documentation

## Overview

ForestGuard uses Celery with Redis as the message broker for background task processing.
Tasks are organized by function and routed to specific queues for optimal resource allocation.

## Worker Configuration

**File:** `celery_app.py`

```python
celery_app = Celery(
    'forestguard',
    broker='redis://redis:6379/0',
    backend='redis://redis:6379/1',
    include=[
        'workers.tasks.ingestion',
        'workers.tasks.clustering',
        'workers.tasks.recovery',
        'workers.tasks.destruction',
    ]
)
```

## Task Inventory

### 1. Data Ingestion Tasks

#### `ingestion.download_firms_daily`
**File:** `workers/tasks/ingestion.py`
**Queue:** `ingestion`
**Schedule:** Daily at 00:00 UTC

Downloads FIRMS (Fire Information for Resource Management System) satellite data from NASA.
This is the primary data source for fire detection.

**Parameters:**
- None (scheduled task)

**Returns:**
- Count of new fire detections ingested

---

### 2. Clustering Tasks

#### `clustering.cluster_detections`
**File:** `workers/tasks/clustering.py`
**Queue:** `clustering`
**Schedule:** Daily at 01:00 UTC

Groups individual fire detections into fire events using DBSCAN spatial clustering.
Applies H3 hexagonal indexing for efficient geospatial queries.

**Parameters:**
- `days_back: int` - Days of data to process (default: 1)

**Returns:**
- Number of clusters created

#### `clustering_task.run_clustering`
**File:** `workers/tasks/clustering_task.py`
**Queue:** `clustering`

Manual trigger for clustering a specific date range.

---

### 3. Analysis Tasks

#### `recovery.analyze_recovery`
**File:** `workers/tasks/recovery.py`
**Queue:** `analysis`

Analyzes vegetation recovery in burnt areas using NDVI indices.
Tracks recovery progress over 36 months post-fire (UC-06).

**Parameters:**
- `fire_event_id: str` - UUID of fire event to analyze

**Returns:**
- Recovery percentage and classification

#### `destruction.detect_destruction`
**File:** `workers/tasks/destruction.py`
**Queue:** `analysis`

Detects land-use changes in areas affected by wildfires.
Supports UC-08 (Land Use Change Detection).

**Parameters:**
- `fire_event_id: str` - UUID of fire event
- `check_date: str` - Date to check for changes

**Returns:**
- Boolean indicating if change was detected

---

### 4. Report Generation Tasks

#### `closure_report_task.generate_closure_report`
**File:** `workers/tasks/closure_report_task.py`
**Queue:** `default`

Generates PDF closure reports for fire episodes.
Includes summary statistics, affected areas, and recovery status.

**Parameters:**
- `episode_id: str` - UUID of the episode

**Returns:**
- Report ID and storage URL

#### `carousel_task.update_carousel`
**File:** `workers/tasks/carousel_task.py`
**Queue:** `default`

Updates the fire event carousel with latest satellite imagery.
Used for the home page display.

**Parameters:**
- `limit: int` - Maximum fires to include (default: 10)

**Returns:**
- Count of updated carousel items

---

### 5. Episode Management Tasks

#### `episode_merge_task.merge_episodes`
**File:** `workers/tasks/episode_merge_task.py`
**Queue:** `default`

Merges related fire events into episodes for GEE optimization (UC-17).
Uses temporal and spatial proximity rules.

**Parameters:**
- `episode_ids: List[str]` - UUIDs of episodes to merge

**Returns:**
- New merged episode ID

---

## Queue Configuration

| Queue | Purpose | Tasks |
|-------|---------|-------|
| `ingestion` | Data ingestion from external sources | download_firms_daily |
| `clustering` | Geospatial clustering operations | cluster_detections, run_clustering |
| `analysis` | CPU-intensive analysis tasks | analyze_recovery, detect_destruction |
| `default` | General purpose tasks | closure reports, carousel updates, merges |

## Scheduled Tasks (Beat)

```python
beat_schedule = {
    'download-firms-daily': {
        'task': 'workers.tasks.ingestion.download_firms_daily',
        'schedule': crontab(hour=0, minute=0),  # 00:00 UTC
        'options': {'queue': 'ingestion'}
    },
    'cluster-daily': {
        'task': 'workers.tasks.clustering.cluster_detections',
        'schedule': crontab(hour=1, minute=0),  # 01:00 UTC
        'kwargs': {'days_back': 1},
        'options': {'queue': 'clustering'}
    },
}
```

## Worker Settings

```python
task_acks_late = True           # Acknowledge after completion
worker_prefetch_multiplier = 1  # One task at a time
task_max_retries = 3            # Retry failed tasks
task_default_retry_delay = 60   # Wait 60s between retries
worker_max_tasks_per_child = 1000  # Recycle workers
```

## Monitoring

Workers can be monitored using:
- **Flower:** `celery -A celery_app flower`
- **Logs:** Check `logs/celery_worker.log`
- **Redis CLI:** `redis-cli LLEN celery` to check queue depth

---

*Last Updated: 2026-02-08*
