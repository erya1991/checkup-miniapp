"""Complete privacy deletion; caller owns commit/rollback and post-commit cleanup."""
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import delete, func, select

from app.confirmation import ConfirmationError
from app.models import (
    ConfirmationItem,
    FileCleanup,
    HealthProfile,
    LabReport,
    LabResult,
    MetricFavorite,
    OcrResultItem,
    OcrTask,
    ReportAsset,
    ReportIngestion,
    UploadAuthorization,
)
from app.models.entities import now
from app.profile_lifecycle import lock_lifecycle

UPLOAD_GRACE = timedelta(seconds=60)


def owned_profile(db, user_id, profile_id, lock=False):
    query = select(HealthProfile).where(HealthProfile.id == profile_id,
        HealthProfile.user_id == user_id, HealthProfile.status == "ACTIVE")
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    profile = db.scalar(query)
    if profile is None:
        raise HTTPException(404, "PROFILE_NOT_FOUND")
    return profile


def deletion_impact(db, user_id, profile_id):
    profile = owned_profile(db, user_id, profile_id)
    ingestions = select(ReportIngestion.id).where(ReportIngestion.health_profile_id == profile_id)

    def count(model, *conditions):
        return db.scalar(select(func.count()).select_from(model).where(*conditions))

    return {"profile": {"id": profile.id, "display_name": profile.display_name},
        "report_count": count(LabReport, LabReport.health_profile_id == profile_id),
        "unfinished_ingestion_count": count(ReportIngestion,
            ReportIngestion.health_profile_id == profile_id, ReportIngestion.status != "CONFIRMED"),
        "total_ingestion_count": count(ReportIngestion, ReportIngestion.health_profile_id == profile_id),
        "favorite_count": count(MetricFavorite, MetricFavorite.health_profile_id == profile_id),
        "processing_ocr_count": count(OcrTask, OcrTask.ingestion_id.in_(ingestions),
                                       OcrTask.status == "PROCESSING")}


def delete_profile(db, user_id, profile_id):
    user = lock_lifecycle(db, user_id)
    profile = owned_profile(db, user_id, profile_id, lock=True)
    scope = select(ReportIngestion.id).where(ReportIngestion.health_profile_id == profile_id)
    # Worker claim/finish lock task BEFORE updating ingestion. Never invert this
    # order: a claim already in flight must finish and be observed as PROCESSING.
    tasks = list(db.scalars(select(OcrTask).where(OcrTask.ingestion_id.in_(scope))
        .order_by(OcrTask.id).with_for_update().execution_options(populate_existing=True)))
    processing = sum(t.status == "PROCESSING" for t in tasks)
    if processing:
        raise ConfirmationError("PROFILE_DELETE_BUSY", processing_count=processing)
    ids = list(db.scalars(scope.order_by(ReportIngestion.id).with_for_update()))
    cleanup_ids = []
    at = now()
    for ingestion_id in ids:
        expiry = db.scalar(select(func.max(UploadAuthorization.expires_at)).where(
            UploadAuthorization.ingestion_id == ingestion_id, UploadAuthorization.expires_at > at))
        prefix = f"users/{user_id}/ingestions/{ingestion_id}/"
        cleanup = db.scalar(select(FileCleanup).where(FileCleanup.cos_object_key == prefix)
                            .with_for_update())
        if cleanup is None:
            cleanup = FileCleanup(cos_object_key=prefix, target_type="PREFIX", status="PENDING")
            db.add(cleanup)
        # Even consumed credentials can still PutObject until their natural expiry.
        cleanup.target_type, cleanup.status = "PREFIX", "PENDING"
        cleanup.not_before = expiry + UPLOAD_GRACE if expiry else None
        db.flush()
        cleanup_ids.append(cleanup.id)
    reports = select(LabReport.id).where(LabReport.health_profile_id == profile_id)
    db.execute(delete(LabResult).where(LabResult.report_id.in_(reports)))
    db.execute(delete(LabReport).where(LabReport.health_profile_id == profile_id))
    db.execute(delete(ConfirmationItem).where(ConfirmationItem.ingestion_id.in_(ids)))
    db.execute(delete(OcrResultItem).where(OcrResultItem.ocr_task_id.in_([t.id for t in tasks])))
    for model in (OcrTask, ReportAsset, UploadAuthorization):
        db.execute(delete(model).where(model.ingestion_id.in_(ids)))
    db.execute(delete(ReportIngestion).where(ReportIngestion.id.in_(ids)))
    db.execute(delete(MetricFavorite).where(MetricFavorite.health_profile_id == profile_id))
    if user.default_health_profile_id == profile_id:
        user.default_health_profile_id = db.scalar(select(HealthProfile.id).where(
            HealthProfile.user_id == user_id, HealthProfile.status == "ACTIVE",
            HealthProfile.id != profile_id).order_by(HealthProfile.created_at, HealthProfile.id).limit(1))
    db.delete(profile)
    db.flush()
    return cleanup_ids
