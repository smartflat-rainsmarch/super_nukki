from celery import Celery

from config import settings

celery_app = Celery(
    "ui2psd",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)


@celery_app.task(bind=True)
def process_image(self, project_id: str):
    self.update_state(state="PROCESSING", meta={"progress": 0})
    return {"project_id": project_id, "status": "completed"}
