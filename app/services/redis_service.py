"""
Cliente Redis compartido para los workers de ForestGuard.

Expone `redis_client` como variable de modulo para que los tests
puedan mockearlo via @patch('app.services.redis_service.redis_client')
o via @patch('workers.tasks.carousel_task.redis_client').
"""
import redis

from app.core.config import settings

redis_client: redis.Redis = redis.from_url(
    getattr(settings, "REDIS_URL", "redis://redis:6379/0"),
    decode_responses=True,
)
