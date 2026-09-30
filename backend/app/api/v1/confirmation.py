"""Authorized confirmation APIs; every write shares the ingestion row lock."""

from contextlib import contextmanager
from datetime import date, time

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.v1.business import asset_data, ingestion_for, profile_data, profile_for
from app.confirmation import (
    REPORT_FIELDS,
    VALUE_FIELDS,
    ConfirmationError,
    add_manual_item,
    assets_for,
    commit_report,
    edit_item,
    ensure_workspace,
)
from app.core.auth import current_user, db_session
from app.models import LabResult, OcrResultItem, StandardMetric, User
from app.models.entities import now

router = APIRouter()
DB_DEP = Depends(db_session)
USER_DEP = Depends(current_user)


@contextmanager
def transaction(db: Session):
    try:
        yield
        db.commit()
    except Exception:
        db.rollback()
        raise


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReportPatch(Input):
    health_profile_id: str | None = Field(default=None, max_length=36)
    hospital_name: str | None = Field(default=None, max_length=256)
    examination_date: str | None = None
    examination_time: str | None = None
    report_no: str | None = Field(default=None, max_length=128)
    report_category: str | None = Field(default=None, max_length=80)


class ItemValues(Input):
    metric_name: str = Field(max_length=256)
    result_text: str = Field(max_length=1024)
    unit_original: str | None = Field(default=None, max_length=128)
    reference_text: str | None = Field(default=None, max_length=1024)
    standard_metric_id: str | None = Field(default=None, max_length=36)


class ItemPatch(Input):
    resolution: str
    metric_name: str | None = Field(default=None, max_length=256)
    result_text: str | None = Field(default=None, max_length=1024)
    unit_original: str | None = Field(default=None, max_length=128)
    reference_text: str | None = Field(default=None, max_length=1024)
    standard_metric_id: str | None = Field(default=None, max_length=36)


class CommitInput(Input):
    duplicate_acknowledgement: str | None = Field(default=None, max_length=64)


def workspace_data(db, user, ingestion, items):
    serialized = []
    for item in items:
        source = db.get(OcrResultItem, item.source_ocr_result_item_id) if item.source_ocr_result_item_id else None
        serialized.append({
            "id": item.id, **{k: getattr(item, k) for k in VALUE_FIELDS},
            "source_ocr_result_item_id": item.source_ocr_result_item_id,
            "source_type": item.source_type, "review_status": item.review_status,
            "resolution": item.resolution,
            "source": None if source is None else {
                "asset_id": source.source_asset_id, "page_no": source.page_no,
                "bbox": source.bbox, "final_decision": source.final_decision,
                "review_reasons": source.review_reasons,
            },
        })
    return {"id": ingestion.id, "status": ingestion.status, "mode": ingestion.mode,
            **{k: getattr(ingestion, k) for k in REPORT_FIELDS},
            "health_profile": profile_data(profile_for(db, user, ingestion.health_profile_id)),
            "assets": [asset_data(a) for a in assets_for(db, ingestion.id)],
            "items": serialized,
            "pending_count": sum(i.review_status == "PENDING" for i in items)}


@router.get("/ingestions/{ingestion_id}/confirmation")
def get_confirmation(ingestion_id: str, user: User = USER_DEP, db: Session = DB_DEP):
    with transaction(db):
        ingestion = ingestion_for(db, user, ingestion_id, lock=True)
        items = ensure_workspace(db, ingestion)
        result = workspace_data(db, user, ingestion, items)
    return result


@router.patch("/ingestions/{ingestion_id}/confirmation")
@router.put("/ingestions/{ingestion_id}/confirmation")
def patch_confirmation(ingestion_id: str, body: ReportPatch,
                       user: User = USER_DEP, db: Session = DB_DEP):
    with transaction(db):
        ingestion = ingestion_for(db, user, ingestion_id, lock=True)
        items = ensure_workspace(db, ingestion)
        changes = body.model_dump(exclude_unset=True)
        if "health_profile_id" in changes:
            profile_for(db, user, changes["health_profile_id"])
        for key, cls in (("examination_date", date), ("examination_time", time)):
            if key in changes and changes[key] is not None:
                try:
                    value = changes[key]
                    if (cls is date and (len(value) != 10 or value[4] != "-" or value[7] != "-")):
                        raise ValueError
                    parsed = cls.fromisoformat(value)
                    if cls is time and parsed.tzinfo is not None:
                        raise ValueError
                    changes[key] = parsed
                except ValueError as exc:
                    raise ConfirmationError("INVALID_REPORT_DATE", 422) from exc
        for key, value in changes.items():
            setattr(ingestion, key, value)
        ingestion.updated_at = now()
        db.flush()
        result = workspace_data(db, user, ingestion, items)
    return result


@router.patch("/ingestions/{ingestion_id}/confirmation/items/{item_id}")
@router.put("/ingestions/{ingestion_id}/confirmation/items/{item_id}")
def patch_item(ingestion_id: str, item_id: str, body: ItemPatch,
               user: User = USER_DEP, db: Session = DB_DEP):
    with transaction(db):
        ingestion = ingestion_for(db, user, ingestion_id, lock=True)
        items = ensure_workspace(db, ingestion)
        item = next((i for i in items if i.id == item_id), None)
        if item is None:
            raise ConfirmationError("CONFIRMATION_ITEM_NOT_FOUND", 404)
        changes = body.model_dump(exclude_unset=True, exclude={"resolution"})
        if any(changes.get(k) is None for k in ("metric_name", "result_text") if k in changes):
            raise ConfirmationError("INVALID_CONFIRMATION_ITEM", 422)
        edit_item(db, item, changes, body.resolution)
        db.flush()
        result = workspace_data(db, user, ingestion, items)
    return result


@router.post("/ingestions/{ingestion_id}/confirmation/items", status_code=201)
def post_item(ingestion_id: str, body: ItemValues, user: User = USER_DEP, db: Session = DB_DEP):
    with transaction(db):
        ingestion = ingestion_for(db, user, ingestion_id, lock=True)
        items = ensure_workspace(db, ingestion)
        item = add_manual_item(db, ingestion, body.model_dump())
        result = workspace_data(db, user, ingestion, [*items, item])
    return result


@router.get("/standard-metrics")
def standard_metrics(q: str = Query(default="", max_length=256),
                     user: User = USER_DEP, db: Session = DB_DEP):
    query = q.strip()
    rows = db.scalars(select(StandardMetric).where(
        StandardMetric.status == "ACTIVE",
        or_(StandardMetric.code.icontains(query, autoescape=True),
            StandardMetric.name.icontains(query, autoescape=True)))
        .order_by(StandardMetric.code).limit(100))
    return [{"id": m.id, "code": m.code, "name": m.name, "status": m.status} for m in rows]


@router.post("/ingestions/{ingestion_id}/manual")
def manual(ingestion_id: str, user: User = USER_DEP, db: Session = DB_DEP):
    with transaction(db):
        ingestion = ingestion_for(db, user, ingestion_id, lock=True)
        profile_for(db, user, ingestion.health_profile_id)
        # Repeated requests after a successful manual transition are safe.
        if (ingestion.status not in {"READY", "OCR_FAILED"}
                and not (ingestion.mode == "MANUAL" and ingestion.status == "PENDING_CONFIRMATION")):
            raise ConfirmationError("COMMIT_NOT_ALLOWED")
        if not assets_for(db, ingestion.id):
            raise ConfirmationError("REPORT_ASSET_REQUIRED")
        ingestion.mode, ingestion.status = "MANUAL", "PENDING_CONFIRMATION"
        if not ingestion.confirmation_initialized_at:
            ingestion.confirmation_initialized_at = now()
        result = workspace_data(db, user, ingestion, ensure_workspace(db, ingestion))
    return result


@router.post("/ingestions/{ingestion_id}/commit")
def commit(ingestion_id: str, body: CommitInput | None = None,
           user: User = USER_DEP, db: Session = DB_DEP):
    with transaction(db):
        ingestion = ingestion_for(db, user, ingestion_id, lock=True)
        report = commit_report(db, ingestion, body.duplicate_acknowledgement if body else None)
        result = {"report_id": report.id, "status": "CONFIRMED",
                  "item_count": db.scalar(select(func.count()).select_from(LabResult)
                                          .where(LabResult.report_id == report.id))}
    return result
