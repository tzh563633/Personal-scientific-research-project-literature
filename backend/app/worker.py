from celery import Celery
from celery.schedules import crontab

from .config import settings

celery_app = Celery("research-platform", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    beat_schedule={
        "excel-update-every-three-hours": {
            "task": "app.worker.update_excel_task",
            "schedule": crontab(minute=0, hour="*/3"),
        },
        "journal-monitor-hourly": {
            "task": "app.worker.monitor_journals_task",
            "schedule": crontab(minute=0),
        },
        "backup-daily": {
            "task": "app.worker.backup_task",
            "schedule": crontab(minute=30, hour=2),
        },
    },
)


@celery_app.task(name="app.worker.process_paper_task")
def process_paper_task(job_id: int) -> None:
    from .db import SessionLocal
    from .services.papers import process_paper

    db = SessionLocal()
    try:
        process_paper(db, job_id)
    finally:
        db.close()


@celery_app.task(name="app.worker.update_excel_task")
def update_excel_task() -> None:
    from .db import SessionLocal
    from .services.excel import generate_excel

    db = SessionLocal()
    try:
        generate_excel(db)
    finally:
        db.close()


@celery_app.task(name="app.worker.update_excel_job_task")
def update_excel_job_task(job_id: int) -> None:
    from .db import SessionLocal
    from .models import Job, now
    from .services.excel import generate_excel

    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job or job.status == "cancelled":
            return
        job.status = "running"
        job.started_at = now()
        job.progress = 10
        db.commit()
        update = generate_excel(db)
        job.progress = 100
        job.status = "succeeded" if update.status == "succeeded" else "failed"
        job.result = {"excel_update_id": update.id}
        job.error = update.error_message
        job.finished_at = now()
        db.commit()
    except Exception as exc:
        db.rollback()
        job = db.get(Job, job_id)
        if job:
            job.status = "failed"
            job.error = str(exc)
            job.finished_at = now()
            db.commit()
    finally:
        db.close()


@celery_app.task(name="app.worker.monitor_journals_task")
def monitor_journals_task() -> None:
    from .db import SessionLocal
    from .services.journals import monitor_journals

    db = SessionLocal()
    try:
        monitor_journals(db)
    finally:
        db.close()


@celery_app.task(name="app.worker.monitor_journals_job_task")
def monitor_journals_job_task(job_id: int) -> None:
    from .db import SessionLocal
    from .models import Job, now
    from .services.journals import monitor_journals

    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job or job.status == "cancelled":
            return
        job.status = "running"
        job.started_at = now()
        job.progress = 10
        db.commit()
        result = monitor_journals(db)
        job.progress = 100
        job.status = "succeeded" if not result["errors"] else "failed"
        job.result = result
        job.error = "; ".join(result["errors"]) if result["errors"] else None
        job.finished_at = now()
        db.commit()
    except Exception as exc:
        db.rollback()
        job = db.get(Job, job_id)
        if job:
            job.status = "failed"
            job.error = str(exc)
            job.finished_at = now()
            db.commit()
    finally:
        db.close()


@celery_app.task(name="app.worker.generate_review_job_task")
def generate_review_job_task(job_id: int) -> None:
    from .db import SessionLocal
    from .models import Job, ReviewFramework, now
    from .services.reviews import generate_review

    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job or job.status == "cancelled":
            return
        framework = db.get(ReviewFramework, job.entity_id)
        if not framework:
            raise ValueError("Review framework is missing")
        job.status = "running"
        job.started_at = now()
        job.progress = 10
        db.commit()
        output = generate_review(db, framework)
        job.progress = 100
        job.status = "succeeded"
        job.result = {"review_output_id": output.id}
        job.finished_at = now()
        db.commit()
    except Exception as exc:
        db.rollback()
        job = db.get(Job, job_id)
        if job:
            job.status = "failed"
            job.error = str(exc)
            job.finished_at = now()
            db.commit()
    finally:
        db.close()


@celery_app.task(name="app.worker.backup_task")
def backup_task() -> None:
    from .services.backup import create_backup

    create_backup()


def enqueue_paper(db, job_id: int) -> None:
    if settings.run_tasks_inline:
        from .services.papers import process_paper

        process_paper(db, job_id)
    else:
        process_paper_task.delay(job_id)


def enqueue_job(db, job_id: int, kind: str) -> None:
    tasks = {
        "excel_update": update_excel_job_task,
        "journal_monitor": monitor_journals_job_task,
        "review_generation": generate_review_job_task,
    }
    task = tasks[kind]
    if settings.run_tasks_inline:
        task.run(job_id)
    else:
        task.delay(job_id)
