"""Authorized formal report APIs; never query confirmation for report contents."""
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import reports
from app.api.v1.confirmation import transaction
from app.cleanup_worker import attempt_cleanup
from app.core.auth import current_user, db_session
from app.core.cos import preview_url
from app.db.session import create_session_factory
from app.models import ReportAsset, User

router = APIRouter(prefix="/reports")
DB_DEP = Depends(db_session)
USER_DEP = Depends(current_user)


@router.get("")
def list_reports(health_profile_id: str, page: int = Query(1, ge=1),
                 page_size: int = Query(20, ge=1, le=100),
                 user: User = USER_DEP, db: Session = DB_DEP):
    return reports.list_reports(db, user, health_profile_id, page, page_size)


@router.get("/{report_id}")
def detail(report_id: str, user: User = USER_DEP, db: Session = DB_DEP):
    return reports.detail(db, user, reports.report_for(db, user, report_id))


@router.get("/{report_id}/assets")
def assets(report_id: str, user: User = USER_DEP, db: Session = DB_DEP):
    report = reports.report_for(db, user, report_id)
    rows = db.scalars(select(ReportAsset).where(ReportAsset.ingestion_id == report.source_ingestion_id)
                      .order_by(ReportAsset.page_no))
    return [{"id": a.id, "page_no": a.page_no, "mime_type": a.mime_type, "file_size": a.file_size}
            for a in rows]


@router.get("/{report_id}/assets/{asset_id}/preview")
def preview(report_id: str, asset_id: str, user: User = USER_DEP, db: Session = DB_DEP):
    report = reports.report_for(db, user, report_id)
    asset = db.scalar(select(ReportAsset).where(
        ReportAsset.id == asset_id, ReportAsset.ingestion_id == report.source_ingestion_id))
    if asset is None:
        raise HTTPException(404, "REPORT_ASSET_NOT_FOUND")
    try:
        url = preview_url(asset.cos_object_key)
    except Exception as exc:
        raise HTTPException(502, "FILE_ACCESS_FAILED") from exc
    return {"url": url, "expires_in": 300}


class MigrateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    health_profile_id: str = Field(min_length=1, max_length=36)
    duplicate_acknowledgement: str | None = Field(default=None, max_length=64)


@router.post("/{report_id}/migrate")
def migrate(report_id: str, body: MigrateInput, user: User = USER_DEP, db: Session = DB_DEP):
    with transaction(db):
        report = reports.migrate_report(db, user, report_id, body.health_profile_id,
                                        body.duplicate_acknowledgement)
        result = reports.detail(db, user, report)
    return result


@router.delete("/{report_id}", status_code=204)
def delete(report_id: str, user: User = USER_DEP, db: Session = DB_DEP):
    with transaction(db):
        cleanup_id = reports.delete_report(db, user, report_id)
    attempt_cleanup(create_session_factory(db.get_bind()), cleanup_id)
    return Response(status_code=204)
