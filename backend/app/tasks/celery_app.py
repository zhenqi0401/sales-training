"""Celery application configuration (stub, ready for AI tasks)."""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "sales_training",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=60 * 60,
    task_soft_time_limit=55 * 60,
)
