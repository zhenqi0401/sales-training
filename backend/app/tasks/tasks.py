"""Celery task definitions."""

from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3)
def generate_questions_task(self, topic: str, count: int = 5, difficulty: int = 2):
    """Background task to generate questions using AI (placeholder).

    Replace the body with actual AI invocation when ready.
    """
    # from app.services.ai_service import generate_questions
    # return await generate_questions(topic, count, difficulty)
    return {
        "status": "pending",
        "message": f"AI question generation for '{topic}' not yet implemented.",
    }
