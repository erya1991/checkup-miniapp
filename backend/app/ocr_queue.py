"""PostgreSQL backed OCR queue. One worker process handles one task at a time."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import OcrTask, ReportIngestion

MAX_ATTEMPTS = 3
BACKOFF = (timedelta(seconds=30), timedelta(minutes=2))


def utcnow() -> datetime:
    return datetime.now(UTC)


def lease_duration() -> timedelta:
    return timedelta(seconds=get_settings().ocr_task_lease_seconds)


def claim(db: Session, worker_id: str, at: datetime | None = None) -> OcrTask | None:
    """Claim a due task atomically; expired leases are eligible for recovery."""
    now = at or utcnow()
    due = or_(
        and_(OcrTask.status == "QUEUED",
             or_(OcrTask.next_attempt_at.is_(None), OcrTask.next_attempt_at <= now)),
        and_(OcrTask.status == "PROCESSING", OcrTask.lease_expires_at <= now),
    )
    while True:
        task = db.scalar(select(OcrTask).where(due).order_by(OcrTask.created_at, OcrTask.id)
                         .with_for_update(skip_locked=True).limit(1))
        if task is None:
            db.commit()
            return None
        if task.attempt_count >= MAX_ATTEMPTS:
            task.status = "FAILED"
            task.last_error_code = "OCR_WORKER_LEASE_EXPIRED"
            task.last_error_message = "Worker lease expired after maximum attempts"
            task.finished_at = now
            task.locked_at = task.lease_expires_at = task.worker_id = None
            db.get(ReportIngestion, task.ingestion_id).status = "OCR_FAILED"
            db.commit()
            continue
        task.status = "PROCESSING"
        task.attempt_count += 1
        task.worker_id = worker_id
        task.locked_at = now
        task.lease_expires_at = now + lease_duration()
        task.next_attempt_at = None
        task.started_at = task.started_at or now
        db.get(ReportIngestion, task.ingestion_id).status = "PROCESSING"
        db.commit()
        return task


def renew(db: Session, task_id: str, worker_id: str) -> bool:
    task = db.get(OcrTask, task_id, with_for_update=True)
    if not task or task.status != "PROCESSING" or task.worker_id != worker_id:
        db.rollback()
        return False
    task.lease_expires_at = utcnow() + lease_duration()
    db.commit()
    return True


def owns_lease(task: OcrTask, worker_id: str) -> bool:
    expiry = task.lease_expires_at
    return (task.status == "PROCESSING" and task.worker_id == worker_id and expiry is not None
            and expiry.replace(tzinfo=UTC) > utcnow())


def fail(db: Session, task_id: str, worker_id: str, code: str,
         recoverable: bool = False) -> bool:
    task = db.get(OcrTask, task_id, with_for_update=True)
    if not task or not owns_lease(task, worker_id):
        db.rollback()
        return False
    task.last_error_code = code
    task.last_error_message = code  # never persist OCR text or exception messages
    task.worker_id = task.locked_at = task.lease_expires_at = None
    if recoverable and task.attempt_count < MAX_ATTEMPTS:
        task.status = "QUEUED"
        task.next_attempt_at = utcnow() + BACKOFF[task.attempt_count - 1]
        db.get(ReportIngestion, task.ingestion_id).status = "QUEUED"
    else:
        task.status = "FAILED"
        task.finished_at = utcnow()
        db.get(ReportIngestion, task.ingestion_id).status = "OCR_FAILED"
    db.commit()
    return True
