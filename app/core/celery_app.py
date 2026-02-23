from celery import Celery
from app.core.config import settings
from app.core.logging import setup_logging

setup_logging()

celery = Celery(
    "resume_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# important: ensure tasks get registered
import app.tasks.analyze_task  # noqa
