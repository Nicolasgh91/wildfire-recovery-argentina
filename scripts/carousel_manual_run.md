# Ejecución manual de generación de thumbnails del carousel

```bash
celery -A workers.celery_app call workers.tasks.carousel_task.generate_carousel --kwargs='{"force_refresh": true}'
```
