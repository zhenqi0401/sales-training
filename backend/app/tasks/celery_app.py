"""Celery application configuration.

⚠️ 当前未启用 — 项目使用 FastAPI BackgroundTasks 处理异步管线。
   如需迁移到 Celery，需要：
   1. 启动 Redis: docker-compose up -d redis（或系统安装的 redis-server）
   2. 启动 Worker: celery -A app.tasks.celery_app worker --loglevel=info
   3. 将 BackgroundTasks.add_task 调用替换为 celery_app.send_task
"""

# Celery 未启用时跳过导入，避免无 Redis 时启动报错
try:
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
except ImportError:
    celery_app = None
