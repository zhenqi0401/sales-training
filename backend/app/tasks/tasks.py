"""Celery task definitions.

⚠️ 当前未启用 — 管线通过 FastAPI BackgroundTasks 在 app/api/v1/videos.py 中执行。
   如需启用 Celery，确保 Redis 可用并启动 worker 进程。
"""

# Stub — 未启用时 celery_app 为 None，任务装饰器不会生效
from app.tasks.celery_app import celery_app

if celery_app is not None:

    @celery_app.task(bind=True, max_retries=3)
    def generate_questions_task(self, topic: str, count: int = 5, difficulty: int = 2):
        """占位任务，暂未实现。"""
        return {
            "status": "pending",
            "message": f"AI question generation for '{topic}' not yet implemented.",
        }
