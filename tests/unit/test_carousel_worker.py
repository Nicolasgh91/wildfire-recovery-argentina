import pytest
from unittest.mock import patch, MagicMock
from workers.tasks.carousel_task import generate_carousel

@patch('workers.tasks.carousel_task.redis_client')
@patch('workers.tasks.carousel_task.ImageryService')
@patch('workers.tasks.carousel_task.SessionLocal')
def test_generate_carousel_lock_acquired(mock_session, mock_service, mock_redis):
    # Setup mock
    mock_redis.set.return_value = True  # Lock acquired
    mock_svc_instance = mock_service.return_value
    mock_svc_instance.run_carousel.return_value = {"processed": 10, "updated": 5, "skipped": 5, "errors": []}

    # Con bind=True, generate_carousel es un objeto Task de Celery.
    # Para invocar la logica directamente en tests se usa .run() que es la funcion real.
    result = generate_carousel.run(max_fires=5)

    assert result["success"] is True
    assert result["processed"] == 10
    mock_redis.set.assert_called_once_with("carousel:generation_lock", "locked", nx=True, ex=3600)
    mock_redis.delete.assert_called_once_with("carousel:generation_lock")

@patch('workers.tasks.carousel_task.redis_client')
def test_generate_carousel_lock_blocked(mock_redis):
    # Setup mock
    mock_redis.set.return_value = False # Lock NOT acquired
    
    result = generate_carousel.run()
    
    assert result["success"] is False
    assert result["reason"] == "lock_acquired_by_another_worker"
    # Si esta bloqueado no debe destruir el lock del otro
    mock_redis.delete.assert_not_called()
