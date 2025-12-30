"""Celery application configuration."""

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "12stones",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.content_tasks",
        "app.workers.voice_tasks",
        "app.workers.narrative_tasks",
        "app.workers.video_tasks",
    ],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,  # Soft limit 55 minutes
    worker_prefetch_multiplier=1,  # Don't prefetch tasks
    task_routes={
        "app.workers.content_tasks.*": {"queue": "content"},
        "app.workers.voice_tasks.*": {"queue": "voice"},
        "app.workers.narrative_tasks.*": {"queue": "narrative"},
        "app.workers.video_tasks.*": {"queue": "video"},
    },
)
