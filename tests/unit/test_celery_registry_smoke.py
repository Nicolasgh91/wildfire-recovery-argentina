from workers.celery_app import celery_app


CRITICAL_TASKS = {
    "workers.tasks.ingestion.download_firms_daily": "workers.tasks.ingestion",
    "workers.tasks.clustering.cluster_detections": "workers.tasks.clustering",
    "workers.tasks.clustering_task.cluster_fire_episodes": "workers.tasks.clustering_task",
    "workers.tasks.carousel_task.generate_carousel": "workers.tasks.carousel_task",
    "workers.tasks.destruction.detect_destruction": "workers.tasks.destruction",
}


def test_celery_registry_smoke_has_expected_tasks_and_modules():
    celery_app.loader.import_default_modules()

    worker_task_names = [
        name for name in celery_app.tasks.keys() if name.startswith("workers.tasks.")
    ]
    assert len(worker_task_names) == len(set(worker_task_names))

    for task_name, expected_module in CRITICAL_TASKS.items():
        assert task_name in celery_app.tasks
        task = celery_app.tasks[task_name]
        assert task.__module__ == expected_module

    for task_name in worker_task_names:
        task = celery_app.tasks[task_name]
        assert task.__module__.startswith("workers.tasks.")
