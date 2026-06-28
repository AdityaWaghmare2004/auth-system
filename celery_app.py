from celery import Celery

celery_app = Celery(
    "auth_system",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
    include=["tasks.email_tasks"]
)