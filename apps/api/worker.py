import traceback
from datetime import datetime, timezone
from pathlib import Path

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

STAGE_PROGRESS = {
    "preprocessing": 10,
    "analyzing": 30,
    "segmenting": 50,
    "inpainting": 70,
    "composing": 85,
    "exporting": 95,
    "completed": 100,
}


def _update_job_status(project_id: str, status: str):
    from database import _get_session_factory
    from models import Job

    session_factory = _get_session_factory()
    db = session_factory()
    try:
        job = db.query(Job).filter(Job.project_id == project_id).first()
        if job:
            job.status = status
            if status == "completed" or status == "failed":
                job.finished_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


def _update_project_status(project_id: str, status: str):
    from database import _get_session_factory
    from models import Project

    session_factory = _get_session_factory()
    db = session_factory()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            project.status = status
            db.commit()
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2)
def process_image(self, project_id: str, image_path: str):
    try:
        _update_project_status(project_id, "processing")

        stages = ["preprocessing", "analyzing", "segmenting", "inpainting", "composing", "exporting"]

        for stage in stages:
            self.update_state(
                state="PROCESSING",
                meta={"stage": stage, "progress": STAGE_PROGRESS[stage]},
            )
            _update_job_status(project_id, stage)

        output_dir = str(Path(settings.storage_path) / "outputs" / project_id)

        from engine.pipeline import run_pipeline
        result = run_pipeline(image_path, output_dir)

        _update_job_status(project_id, "completed")
        _update_project_status(project_id, "done")

        self.update_state(
            state="SUCCESS",
            meta={"stage": "completed", "progress": 100},
        )

        return {
            "project_id": project_id,
            "status": "completed",
            "psd_path": result.psd_result.psd_path,
            "manifest_path": result.manifest_path,
            "text_count": result.text_count,
            "element_count": result.element_count,
            "inpaint_quality": result.inpaint_quality,
        }

    except Exception as exc:
        _update_job_status(project_id, "failed")
        _update_project_status(project_id, "failed")
        raise self.retry(exc=exc, countdown=30)
