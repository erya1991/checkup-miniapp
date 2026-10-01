"""Stage 04 safety gate. Callers hold the ingestion lock and own the transaction."""

import hashlib
import hmac
import json
import re
import unicodedata
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.metric_identity import active_dictionary, resolve_exact
from app.models import (
    ConfirmationItem,
    HealthProfile,
    LabReport,
    LabResult,
    OcrResultItem,
    OcrTask,
    ReportAsset,
    ReportIngestion,
    StandardMetric,
)
from app.models.entities import now

VALUE_FIELDS = (
    "sequence_no", "metric_name", "standard_metric_id", "result_text", "result_numeric",
    "comparator", "unit_original", "unit_normalized", "reference_text", "reference_low",
    "reference_high", "abnormal",
)
REPORT_FIELDS = (
    "health_profile_id", "hospital_name", "examination_date", "examination_time",
    "report_no", "report_category",
)
EDIT_FIELDS = {"metric_name", "result_text", "unit_original", "reference_text", "standard_metric_id"}
RESOLUTIONS = {"ACCEPTED", "CORRECTED", "STANDARD_METRIC_SELECTED", "KEEP_ORIGINAL_NAME", "REMOVED"}
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"


class ConfirmationError(Exception):
    def __init__(self, code: str, status: int = 409, **details):
        self.code, self.status, self.details = code, status, details
        super().__init__(code)


def editable(ingestion: ReportIngestion) -> None:
    if ingestion.status == "CONFIRMED":
        raise ConfirmationError("CONFIRMATION_LOCKED")
    if ingestion.status != "PENDING_CONFIRMATION":
        raise ConfirmationError("CONFIRMATION_NOT_READY")


def items_for(db: Session, ingestion_id: str) -> list[ConfirmationItem]:
    return list(db.scalars(select(ConfirmationItem).where(
        ConfirmationItem.ingestion_id == ingestion_id).order_by(ConfirmationItem.sequence_no)))


def assets_for(db: Session, ingestion_id: str) -> list[ReportAsset]:
    return list(db.scalars(select(ReportAsset).where(
        ReportAsset.ingestion_id == ingestion_id, ReportAsset.upload_status == "UPLOADED")
        .order_by(ReportAsset.page_no)))


def source_rows(db: Session, ingestion: ReportIngestion) -> list[OcrResultItem]:
    task = db.scalar(select(OcrTask).where(OcrTask.ingestion_id == ingestion.id)
                     .order_by(OcrTask.run_no.desc()).limit(1))
    if task is None or task.status != "SUCCEEDED":
        raise ConfirmationError("CONFIRMATION_SOURCE_INVALID")
    rows = list(db.scalars(select(OcrResultItem).where(OcrResultItem.ocr_task_id == task.id)
                           .order_by(OcrResultItem.sequence_no)))
    summary = task.result_summary or {}
    if not isinstance(summary, dict) or not isinstance(task.input_manifest, list):
        raise ConfirmationError("CONFIRMATION_SOURCE_INVALID")
    total = summary.get("total_count")
    assets = {a.id: a.page_no for a in assets_for(db, ingestion.id)}
    manifest = {a["asset_id"]: a["page_no"] for a in task.input_manifest
                if isinstance(a, dict) and "asset_id" in a and "page_no" in a}
    if (type(total) is not int or total != len(rows)
            or len(manifest) != len(task.input_manifest)
            or any(assets.get(asset_id) != page_no for asset_id, page_no in manifest.items())
            or [r.sequence_no for r in rows] != list(range(1, len(rows) + 1))
            or any(r.final_decision not in {"FINAL_AUTO", "FINAL_REVIEW"}
                   or assets.get(r.source_asset_id) != r.page_no
                   or manifest.get(r.source_asset_id) != r.page_no for r in rows)):
        raise ConfirmationError("CONFIRMATION_SOURCE_INVALID")
    return rows


def ensure_workspace(db: Session, ingestion: ReportIngestion) -> list[ConfirmationItem]:
    editable(ingestion)
    items = items_for(db, ingestion.id)
    if ingestion.mode == "MANUAL":
        if not ingestion.confirmation_initialized_at or any(
                i.source_ocr_result_item_id is not None for i in items):
            raise ConfirmationError("CONFIRMATION_SOURCE_INVALID")
        return items
    if ingestion.mode != "OCR":
        raise ConfirmationError("CONFIRMATION_SOURCE_INVALID")
    rows = source_rows(db, ingestion)
    expected = {r.id for r in rows}
    existing = {i.source_ocr_result_item_id for i in items if i.source_ocr_result_item_id}
    if ingestion.confirmation_initialized_at:
        if expected != existing:
            raise ConfirmationError("CONFIRMATION_SOURCE_INVALID")
        return items
    if items:
        raise ConfirmationError("CONFIRMATION_SOURCE_INVALID")
    dictionary = active_dictionary(db, lock=True)
    for row in rows:
        metric_id, reliable_code = resolve_exact(dictionary, row.standard_metric_code, row.raw_metric)
        # Product exact resolution may prefill an identity, never raise OCR trust.
        auto = row.final_decision == "FINAL_AUTO" and reliable_code
        db.add(ConfirmationItem(
            ingestion_id=ingestion.id, source_ocr_result_item_id=row.id,
            sequence_no=row.sequence_no, metric_name=row.raw_metric or "",
            standard_metric_id=metric_id,
            result_text=row.result_text or "", result_numeric=row.result_numeric,
            comparator=row.comparator, unit_original=row.raw_unit,
            unit_normalized=row.normalized_unit, reference_text=row.reference_text,
            reference_low=row.reference_low, reference_high=row.reference_high,
            abnormal=row.abnormal,
            source_type="OCR_AUTO" if row.final_decision == "FINAL_AUTO" else "OCR_CORRECTED",
            review_status="RESOLVED" if auto else "PENDING",
            resolution="ACCEPTED" if auto else None,
        ))
    ingestion.confirmation_initialized_at = now()
    db.flush()
    return items_for(db, ingestion.id)


def active_metric(db: Session, metric_id: str | None) -> None:
    if metric_id is not None and not db.scalar(select(StandardMetric.id).where(
            StandardMetric.id == metric_id, StandardMetric.status == "ACTIVE")
            .with_for_update(read=True)):
        raise ConfirmationError("STANDARD_METRIC_NOT_FOUND", 422)


def parse_manual_fields(item: ConfirmationItem, changed: set[str]) -> None:
    """Conservative text parsing, no medical inference or unit conversion."""
    if "result_text" in changed:
        match = re.fullmatch(rf"\s*(<=|>=|<|>|≤|≥|=)?\s*({NUMBER})\s*", item.result_text)
        item.result_numeric = Decimal(match[2]) if match else None
        item.comparator = ({"≤": "<=", "≥": ">="}.get(match[1], match[1]) or "=") if match else None
    if "reference_text" in changed:
        match = re.fullmatch(rf"\s*({NUMBER})\s*(?:~|～|–|—|-)\s*({NUMBER})\s*",
                             item.reference_text or "")
        item.reference_low = item.reference_high = None
        if match and Decimal(match[1]) <= Decimal(match[2]):
            item.reference_low, item.reference_high = Decimal(match[1]), Decimal(match[2])
    if "unit_original" in changed:
        # A new unit is user text, not a Pipeline-normalized identity.
        item.unit_normalized = None
    if changed & {"result_text", "reference_text", "unit_original", "standard_metric_id"}:
        item.abnormal = None


def edit_item(db: Session, item: ConfirmationItem, changes: dict, resolution: str) -> None:
    if resolution not in RESOLUTIONS or set(changes) - EDIT_FIELDS:
        raise ConfirmationError("INVALID_CONFIRMATION_ITEM", 422)
    if resolution in {"ACCEPTED", "REMOVED"} and changes:
        raise ConfirmationError("INVALID_CONFIRMATION_ITEM", 422)
    if resolution == "STANDARD_METRIC_SELECTED" and (
            not changes.get("standard_metric_id") or set(changes) != {"standard_metric_id"}):
        raise ConfirmationError("INVALID_CONFIRMATION_ITEM", 422)
    if resolution == "KEEP_ORIGINAL_NAME" and changes.get("standard_metric_id"):
        raise ConfirmationError("INVALID_CONFIRMATION_ITEM", 422)
    active_metric(db, changes.get("standard_metric_id"))
    actual_changes = {k for k, v in changes.items() if getattr(item, k) != v}
    for name, value in changes.items():
        setattr(item, name, value)
    if resolution == "KEEP_ORIGINAL_NAME":
        if item.standard_metric_id:
            actual_changes.add("standard_metric_id")
        item.standard_metric_id = None
    parse_manual_fields(item, actual_changes)
    if resolution != "REMOVED" and (not item.metric_name.strip() or not item.result_text.strip()):
        raise ConfirmationError("INVALID_CONFIRMATION_ITEM", 422)
    if item.source_ocr_result_item_id:
        if resolution != "REMOVED" and resolution != "KEEP_ORIGINAL_NAME" and not item.standard_metric_id:
            # Unknown OCR identities need an explicit keep-original or selection.
            raise ConfirmationError("STANDARD_METRIC_NOT_FOUND", 422)
        if actual_changes:
            item.source_type = "OCR_CORRECTED"
    item.review_status = "RESOLVED"
    item.resolution = resolution
    item.updated_at = now()


def add_manual_item(db: Session, ingestion: ReportIngestion, values: dict) -> ConfirmationItem:
    active_metric(db, values.get("standard_metric_id"))
    if not values["metric_name"].strip() or not values["result_text"].strip():
        raise ConfirmationError("INVALID_CONFIRMATION_ITEM", 422)
    sequence = db.scalar(select(func.max(ConfirmationItem.sequence_no)).where(
        ConfirmationItem.ingestion_id == ingestion.id)) or 0
    item = ConfirmationItem(ingestion_id=ingestion.id, sequence_no=sequence + 1,
                            **values, source_type="MANUAL", review_status="RESOLVED",
                            resolution="MANUAL_ADDED")
    parse_manual_fields(item, set(values))
    db.add(item)
    db.flush()
    return item


def normalized(text: str | None) -> str:
    return "".join(unicodedata.normalize("NFKC", text or "").casefold().split())


def metric_set(items) -> set[str]:
    return {"id:" + i.standard_metric_id if i.standard_metric_id else "name:" + normalized(i.metric_name)
            for i in items}


def duplicate_check(db: Session, ingestion: ReportIngestion,
                    items: list[ConfirmationItem]) -> tuple[list[dict], str]:
    kept = [i for i in items if i.resolution != "REMOVED"]
    current_set = metric_set(kept)
    candidates = []
    reports = db.scalars(select(LabReport).where(
        LabReport.user_id == ingestion.user_id,
        LabReport.health_profile_id == ingestion.health_profile_id).order_by(LabReport.id))
    for report in reports:
        hospital = normalized(ingestion.hospital_name)
        same_hospital = hospital == normalized(report.hospital_name)
        strong = (bool(normalized(ingestion.report_no))
                  and normalized(ingestion.report_no) == normalized(report.report_no)
                  and (same_hospital or not hospital or not normalized(report.hospital_name)))
        results = list(db.scalars(select(LabResult).where(LabResult.report_id == report.id)))
        old_set = metric_set(results)
        union = current_set | old_set
        overlap = len(current_set & old_set) / len(union) if union else 0
        combined = (bool(hospital) and same_hospital
                    and ingestion.examination_date == report.examination_date and overlap >= 0.8)
        if strong or combined:
            candidates.append({
                "report_id": report.id, "hospital_name": report.hospital_name,
                "examination_date": report.examination_date, "report_no": report.report_no,
                "item_count": len(results), "reason": "REPORT_NO" if strong else "DATE_HOSPITAL_METRICS",
            })
    # Bind both final data and each save version, plus the current candidate set.
    payload = {"ingestion_id": ingestion.id,
               "report": {k: getattr(ingestion, k) for k in REPORT_FIELDS},
               "items": [{"id": i.id, **{k: getattr(i, k) for k in VALUE_FIELDS},
                          "resolution": i.resolution, "review_status": i.review_status,
                          "source_type": i.source_type, "updated_at": i.updated_at} for i in items],
               "updated_at": ingestion.updated_at,
               "candidates": candidates}
    digest = hmac.new(get_settings().jwt_secret.encode(),
                      json.dumps(payload, sort_keys=True, default=str).encode(), hashlib.sha256).hexdigest()
    return candidates, digest


def commit_report(db: Session, ingestion: ReportIngestion,
                  acknowledgement: str | None = None) -> LabReport:
    """No commit/COS operations here; caller commits once or rolls back all changes."""
    if ingestion.status == "CONFIRMED":
        report = db.scalar(select(LabReport).where(LabReport.source_ingestion_id == ingestion.id))
        if report is None:
            raise ConfirmationError("COMMIT_NOT_ALLOWED")
        return report
    # Serialize same-profile commits too, so a concurrently saved duplicate is
    # visible before the final duplicate check (PostgreSQL READ COMMITTED).
    if not db.scalar(select(HealthProfile.id).where(
            HealthProfile.id == ingestion.health_profile_id,
            HealthProfile.user_id == ingestion.user_id, HealthProfile.status == "ACTIVE")
            .with_for_update()):
        raise ConfirmationError("PROFILE_NOT_FOUND", 404)
    if not ingestion.confirmation_initialized_at:
        raise ConfirmationError("CONFIRMATION_NOT_READY")
    items = ensure_workspace(db, ingestion)
    if not isinstance(ingestion.examination_date, date):
        raise ConfirmationError("INVALID_REPORT_DATE", 422)
    if not assets_for(db, ingestion.id):
        raise ConfirmationError("REPORT_ASSET_REQUIRED")
    pending = sum(i.review_status != "RESOLVED" for i in items)
    if pending:
        raise ConfirmationError("REVIEW_PENDING", pending_count=pending)
    kept = [i for i in items if i.resolution != "REMOVED"]
    if not kept:
        raise ConfirmationError("NO_REPORT_ITEMS")
    for item in kept:
        if (not item.metric_name.strip() or not item.result_text.strip()
                or item.resolution is None or item.source_type not in {"OCR_AUTO", "OCR_CORRECTED", "MANUAL"}
                or (item.resolution == "KEEP_ORIGINAL_NAME" and item.standard_metric_id is not None)):
            raise ConfirmationError("INVALID_CONFIRMATION_ITEM", 422)
        active_metric(db, item.standard_metric_id)
    db.flush()
    candidates, fingerprint = duplicate_check(db, ingestion, items)
    if candidates and not hmac.compare_digest(acknowledgement or "", fingerprint):
        raise ConfirmationError("DUPLICATE_CONFIRM_REQUIRED", candidates=candidates,
                                acknowledgement=fingerprint)
    report = LabReport(user_id=ingestion.user_id, source_ingestion_id=ingestion.id,
                       **{k: getattr(ingestion, k) for k in REPORT_FIELDS},
                       has_manual_correction=any(i.source_type == "OCR_CORRECTED" for i in kept),
                       has_manual_items=any(i.source_type == "MANUAL" for i in kept))
    db.add(report)
    db.flush()
    for item in kept:
        db.add(LabResult(report_id=report.id, health_profile_id=ingestion.health_profile_id,
                         source_confirmation_item_id=item.id, data_source=item.source_type,
                         examination_date=ingestion.examination_date,
                         examination_time=ingestion.examination_time,
                         **{k: getattr(item, k) for k in VALUE_FIELDS}))
    ingestion.status = "CONFIRMED"
    ingestion.confirmed_at = now()
    db.flush()
    return report
