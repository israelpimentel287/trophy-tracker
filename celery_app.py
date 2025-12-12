import os
from celery import Celery
from config import Config

def make_celery():
    celery = Celery('trophy_tracker')

    celery.conf.update(
        broker_url=Config.broker_url,
        result_backend=Config.result_backend,
        task_serializer=Config.task_serializer,
        result_serializer=Config.result_serializer,
        accept_content=Config.accept_content,
        timezone=Config.timezone,
        enable_utc=Config.enable_utc,
        task_annotations=Config.task_annotations,
        task_routes=Config.task_routes,
        worker_prefetch_multiplier=Config.worker_prefetch_multiplier,
        task_acks_late=Config.task_acks_late,
        worker_max_tasks_per_child=Config.worker_max_tasks_per_child,
        task_track_started=Config.task_track_started,
        worker_send_task_events=Config.worker_send_task_events,
        task_send_sent_event=Config.task_send_sent_event,
        worker_pool=Config.worker_pool,
        worker_concurrency=Config.worker_concurrency,
        worker_disable_rate_limits=Config.worker_disable_rate_limits
    )

    return celery

celery_app = make_celery()

try:
    from app import app as flask_app

    class ContextTask(celery_app.Task):
        def __call__(self, *args, **kwargs):
            with flask_app.app_context():
                return self.run(*args, **kwargs)

    celery_app.Task = ContextTask

    from app import tasks, steam_api

    print("Celery initialized with Flask context")
except ImportError as e:
    print(f"Warning: Could not import Flask app: {e}")

if __name__ == "__main__":
    celery_app.start()