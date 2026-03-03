# Scripts Directory

This directory contains organized utility and administrative scripts for the wildfire recovery project.

## Directory Structure

### admin/
Administrative and monitoring scripts for database operations and system health checks.

- **check_batch_status.py** - Monitors recent vegetation monitoring records and processing status
- **check_progress.py** - Shows database progress with record counts and recent activity
- **check_schema.py** - Inspects database schema and sample data
- **count_episodes.py** - Counts fire episodes and provides statistics by status
- **count_events.py** - Counts eligible fire events by year for planning
- **get_fire_id.py** - Gets the most recent fire event ID
- **get_latest_event.py** - Gets the latest processed event from monitoring tables
- **get_recent_episodes_fixed.py** - Retrieves recent episodes for backfill operations
- **monitor_backfill.py** - Real-time monitoring script for historical backfill operations
- **verify_data.py** - Verifies processed data integrity

### triggers/
Scripts to trigger various Celery tasks and batch operations.

- **batch_recent.py** - Triggers batch recovery analysis for recent events
- **trigger_backfill_vm.py** - Triggers historical backfill for vegetation monitoring
- **trigger_destruction.py** - Triggers destruction detection for a specific event
- **trigger_episode_batch.py** - Triggers batch episode recovery analysis
- **trigger_historical_backfill.py** - Triggers complete historical backfill (2015-2025)
- **trigger_historical_backfill_monitored.py** - Triggers backfill with automatic monitoring
- **trigger_recovery.py** - Simple trigger for recovery analysis of a specific event

## Usage

### Admin Scripts
```bash
# Check database progress
python scripts/admin/check_progress.py

# Monitor backfill operations
python scripts/admin/monitor_backfill.py <task_id>

# Count episodes and events
python scripts/admin/count_episodes.py
python scripts/admin/count_events.py
```

### Trigger Scripts
```bash
# Trigger recent batch processing
python scripts/triggers/batch_recent.py

# Trigger historical backfill
python scripts/triggers/trigger_historical_backfill.py

# Trigger with monitoring
python scripts/triggers/trigger_historical_backfill_monitored.py
```

## Notes

- All scripts require the virtual environment to be activated
- Database scripts use the app's SessionLocal for database connections
- Trigger scripts require Celery workers to be running
- Monitor scripts are designed for real-time progress tracking
