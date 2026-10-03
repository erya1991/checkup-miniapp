"""Formal report management. Callers own the database transaction."""
import hashlib
import hmac
import json

from fastapi import HTTPException
from sqlalchemy import delete, func, select, update

from app.api.v1.business import profile_data, profile_for
from app.confirmation import REPORT_FIELDS, VALUE_FIELDS, ConfirmationError, metric_set, normalized
from app.core.config import get_settings
from app.models import (
    ConfirmationItem,
    FileCleanup,
    HealthProfile,
    LabReport,
    LabResult,
    OcrResultItem,
    OcrTask,
    ReportAsset,
    ReportIngestion,
    StandardMetric,
    UploadAuthorization,
)
from app.profile_lifecycle import lock_lifecycle


def report_for(db, user, report_id, lock=False):
    query = select(LabReport).where(LabReport.id == report_id, LabReport.user_id == user.id)
    if lock:
        lock_lifecycle(db, user.id)
        query = query.with_for_update().execution_options(populate_existing=True)
    report = db.scalar(query)
    if report is None:
        raise HTTPException(404, "REPORT_NOT_FOUND")
    profile_for(db, user, report.health_profile_id)
    return report


def results_for(db, report_id):
    return list(db.scalars(select(LabResult).where(LabResult.report_id == report_id)
                           .order_by(LabResult.sequence_no)))


def summary(db, report):
    rows = results_for(db, report.id)
    return {"id": report.id, **{k: getattr(report, k) for k in REPORT_FIELDS},
            "item_count": len(rows),
            "abnormal_count": sum(r.abnormal not in (None, "", "NORMAL") for r in rows)}


def detail(db, user, report):
    rows = []
    for result in results_for(db, report.id):
        metric = db.get(StandardMetric, result.standard_metric_id) if result.standard_metric_id else None
        rows.append({"id": result.id, **{k: getattr(result, k) for k in VALUE_FIELDS},
                     "data_source": result.data_source,
                     "standard_metric": {"id": metric.id, "code": metric.code, "name": metric.name}
                     if metric else None})
    return {**summary(db, report),
            "health_profile": profile_data(profile_for(db, user, report.health_profile_id)),
            "results": rows}


def list_reports(db, user, profile_id, page, page_size):
    profile_for(db, user, profile_id)
    conditions = (LabReport.user_id == user.id, LabReport.health_profile_id == profile_id)
    total = db.scalar(select(func.count()).select_from(LabReport).where(*conditions))
    rows = db.scalars(select(LabReport).where(*conditions).order_by(
        LabReport.examination_date.desc(), LabReport.examination_time.desc().nulls_last(),
        LabReport.created_at.desc(), LabReport.id.desc()).offset((page - 1) * page_size).limit(page_size))
    return {"items": [summary(db, row) for row in rows], "total": total,
            "page": page, "page_size": page_size, "has_more": page * page_size < total}


def migration_duplicates(db, report, target_id):
    current_set = metric_set(results_for(db, report.id))
    candidates = []
    for other in db.scalars(select(LabReport).where(
            LabReport.user_id == report.user_id, LabReport.health_profile_id == target_id,
            LabReport.id != report.id).order_by(LabReport.id)):
        hospital = normalized(report.hospital_name)
        same_hospital = hospital == normalized(other.hospital_name)
        strong = (bool(normalized(report.report_no))
                  and normalized(report.report_no) == normalized(other.report_no)
                  and (same_hospital or not hospital or not normalized(other.hospital_name)))
        other_results = results_for(db, other.id)
        other_set = metric_set(other_results)
        union = current_set | other_set
        overlap = len(current_set & other_set) / len(union) if union else 0
        combined = (bool(hospital) and same_hospital
                    and report.examination_date == other.examination_date and overlap >= 0.8)
        if strong or combined:
            candidates.append({"report_id": other.id, "hospital_name": other.hospital_name,
                               "examination_date": other.examination_date, "report_no": other.report_no,
                               "item_count": len(other_results),
                               "reason": "REPORT_NO" if strong else "DATE_HOSPITAL_METRICS"})
    payload = {"report_id": report.id, "target_health_profile_id": target_id,
               "report": {k: getattr(report, k) for k in REPORT_FIELDS},
               "metric_set": sorted(current_set), "candidates": candidates}
    digest = hmac.new(get_settings().jwt_secret.encode(),
                      json.dumps(payload, sort_keys=True, default=str).encode(), hashlib.sha256).hexdigest()
    return candidates, digest


def migrate_report(db, user, report_id, target_id, acknowledgement=None):
    report = report_for(db, user, report_id, lock=True)
    if target_id == report.health_profile_id:
        return report
    # Same lock order for migrate/delete; source ingestion is also shared with commit retry.
    ingestion = db.scalar(select(ReportIngestion).where(
        ReportIngestion.id == report.source_ingestion_id, ReportIngestion.user_id == user.id)
        .with_for_update().execution_options(populate_existing=True))
    if ingestion is None:
        raise HTTPException(404, "REPORT_NOT_FOUND")
    target = db.scalar(select(HealthProfile).where(
        HealthProfile.id == target_id, HealthProfile.user_id == user.id,
        HealthProfile.status == "ACTIVE").with_for_update())
    if target is None:
        raise HTTPException(404, "PROFILE_NOT_FOUND")
    candidates, digest = migration_duplicates(db, report, target_id)
    if candidates and not hmac.compare_digest(acknowledgement or "", digest):
        raise ConfirmationError("DUPLICATE_CONFIRM_REQUIRED", candidates=candidates, acknowledgement=digest)
    ingestion.health_profile_id = target_id
    report.health_profile_id = target_id
    db.execute(update(LabResult).where(LabResult.report_id == report.id).values(health_profile_id=target_id))
    db.flush()
    return report


def delete_report(db, user, report_id):
    report = report_for(db, user, report_id, lock=True)
    ingestion_id = report.source_ingestion_id
    db.scalar(select(ReportIngestion).where(ReportIngestion.id == ingestion_id).with_for_update())
    prefix = f"users/{user.id}/ingestions/{ingestion_id}/"
    cleanup = FileCleanup(cos_object_key=prefix, target_type="PREFIX", status="PENDING")
    db.add(cleanup)
    db.flush()  # A cleanup persistence failure must prevent any committed medical deletion.
    db.execute(delete(LabResult).where(LabResult.report_id == report.id))
    db.execute(delete(LabReport).where(LabReport.id == report.id))
    db.execute(delete(ConfirmationItem).where(ConfirmationItem.ingestion_id == ingestion_id))
    tasks = select(OcrTask.id).where(OcrTask.ingestion_id == ingestion_id)
    db.execute(delete(OcrResultItem).where(OcrResultItem.ocr_task_id.in_(tasks)))
    db.execute(delete(OcrTask).where(OcrTask.ingestion_id == ingestion_id))
    db.execute(delete(ReportAsset).where(ReportAsset.ingestion_id == ingestion_id))
    db.execute(delete(UploadAuthorization).where(UploadAuthorization.ingestion_id == ingestion_id))
    db.execute(delete(ReportIngestion).where(ReportIngestion.id == ingestion_id))
    db.flush()
    return cleanup.id
