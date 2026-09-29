"""Stage 03 OCR task creation and status APIs."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.business import ingestion_for
from app.core.auth import current_user, db_session
from app.models import OcrTask, ReportAsset, ReportIngestion, User
from app.ocr_pipeline import PIPELINE_VERSION

router = APIRouter()
DB_DEP = Depends(db_session)
USER_DEP = Depends(current_user)


def latest(db: Session, ingestion_id: str) -> OcrTask | None:
    return db.scalar(select(OcrTask).where(OcrTask.ingestion_id == ingestion_id)
                     .order_by(OcrTask.run_no.desc()).limit(1))


def summary(ingestion: ReportIngestion, task: OcrTask | None) -> dict:
    return {
        "ingestion_status": ingestion.status,
        "task": None if task is None else {
            "id": task.id, "run_no": task.run_no, "status": task.status,
            "attempt_count": task.attempt_count,
            "started_at": task.started_at, "finished_at": task.finished_at,
            "result_summary": task.result_summary if task.status == "SUCCEEDED" else None,
            "error_code": task.last_error_code if task.status == "FAILED" else None,
        },
    }


def manifest(db: Session, ingestion_id: str) -> list[dict]:
    assets = db.scalars(select(ReportAsset).where(ReportAsset.ingestion_id == ingestion_id,
                                                  ReportAsset.upload_status == "UPLOADED")
                        .order_by(ReportAsset.page_no)).all()
    if not assets:
        raise HTTPException(409, "OCR_INPUT_EMPTY")
    if [a.page_no for a in assets] != list(range(1, len(assets) + 1)):
        raise HTTPException(409, "OCR_INPUT_ORDER_INVALID")
    return [{"asset_id": a.id, "page_no": a.page_no, "cos_object_key": a.cos_object_key,
             "mime_type": a.mime_type, "file_size": a.file_size} for a in assets]


@router.post("/ingestions/{ingestion_id}/recognize")
def recognize(ingestion_id: str, user: User = USER_DEP, db: Session = DB_DEP):
    ingestion = ingestion_for(db, user, ingestion_id, lock=True)
    task = latest(db, ingestion_id)
    if ingestion.status in {"QUEUED", "PROCESSING", "PENDING_CONFIRMATION"} and task:
        return summary(ingestion, task)
    if ingestion.status != "READY" or task is not None:
        raise HTTPException(409, "OCR_RECOGNIZE_NOT_ALLOWED")
    task = OcrTask(ingestion_id=ingestion.id, run_no=1, status="QUEUED",
                   pipeline_version=PIPELINE_VERSION,
                   input_manifest=manifest(db, ingestion.id))
    db.add(task)
    ingestion.status = "QUEUED"
    db.commit()
    return summary(ingestion, task)


@router.get("/ingestions/{ingestion_id}/ocr")
def get_ocr(ingestion_id: str, user: User = USER_DEP, db: Session = DB_DEP):
    ingestion = ingestion_for(db, user, ingestion_id)
    return summary(ingestion, latest(db, ingestion_id))


@router.post("/ingestions/{ingestion_id}/ocr/retry")
def retry(ingestion_id: str, user: User = USER_DEP, db: Session = DB_DEP):
    ingestion = ingestion_for(db, user, ingestion_id, lock=True)
    previous = latest(db, ingestion_id)
    if ingestion.status in {"QUEUED", "PROCESSING"} and previous and previous.run_no > 1:
        return summary(ingestion, previous)
    if ingestion.status != "OCR_FAILED" or not previous or previous.status != "FAILED":
        raise HTTPException(409, "OCR_RETRY_NOT_ALLOWED")
    task = OcrTask(ingestion_id=ingestion.id, run_no=previous.run_no + 1,
                   pipeline_version=PIPELINE_VERSION,
                   status="QUEUED", input_manifest=manifest(db, ingestion.id))
    db.add(task)
    ingestion.status = "QUEUED"
    db.commit()
    return summary(ingestion, task)
