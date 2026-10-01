from datetime import UTC, date, datetime, time
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def uid() -> str:
    return str(uuid4())


def now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    wechat_openid: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE")
    default_health_profile_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    last_login_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class HealthProfile(Base):
    __tablename__ = "health_profiles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    display_name: Mapped[str] = mapped_column(String(80))
    relation: Mapped[str] = mapped_column(String(16))
    gender: Mapped[str | None] = mapped_column(String(16), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class ReportIngestion(Base):
    __tablename__ = "report_ingestions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    health_profile_id: Mapped[str] = mapped_column(ForeignKey("health_profiles.id"), index=True)
    mode: Mapped[str] = mapped_column(String(16), default="OCR")
    status: Mapped[str] = mapped_column(String(32), default="UPLOADING")
    hospital_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    examination_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    examination_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    report_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    report_category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    confirmation_initialized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class UploadAuthorization(Base):
    __tablename__ = "upload_authorizations"
    object_key: Mapped[str] = mapped_column(String(256), primary_key=True)
    ingestion_id: Mapped[str] = mapped_column(ForeignKey("report_ingestions.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReportAsset(Base):
    __tablename__ = "report_assets"
    __table_args__ = (UniqueConstraint("ingestion_id", "page_no"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    ingestion_id: Mapped[str] = mapped_column(ForeignKey("report_ingestions.id"), index=True)
    cos_object_key: Mapped[str] = mapped_column(String(256), unique=True)
    page_no: Mapped[int] = mapped_column(Integer)
    mime_type: Mapped[str] = mapped_column(String(32))
    file_size: Mapped[int] = mapped_column(Integer)
    upload_status: Mapped[str] = mapped_column(String(16), default="UPLOADED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FileCleanup(Base):
    __tablename__ = "file_cleanups"
    __table_args__ = (CheckConstraint(
        "target_type IN ('OBJECT', 'PREFIX')", name="ck_file_cleanup_target_type"),)
    target_type: Mapped[str] = mapped_column(String(16), default="OBJECT", server_default="OBJECT")
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    cos_object_key: Mapped[str] = mapped_column(String(256), unique=True)
    status: Mapped[str] = mapped_column(String(16), default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class OcrTask(Base):
    __tablename__ = "ocr_tasks"
    __table_args__ = (UniqueConstraint("ingestion_id", "run_no"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    ingestion_id: Mapped[str] = mapped_column(ForeignKey("report_ingestions.id"), index=True)
    run_no: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="QUEUED", index=True)
    pipeline_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    input_manifest: Mapped[list] = mapped_column(JSON)
    report_candidates: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    artifact_root: Mapped[str | None] = mapped_column(String(512), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    worker_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class OcrResultItem(Base):
    __tablename__ = "ocr_result_items"
    __table_args__ = (UniqueConstraint("ocr_task_id", "sequence_no"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    ocr_task_id: Mapped[str] = mapped_column(ForeignKey("ocr_tasks.id"), index=True)
    sequence_no: Mapped[int] = mapped_column(Integer)
    source_asset_id: Mapped[str] = mapped_column(ForeignKey("report_assets.id"))
    page_no: Mapped[int] = mapped_column(Integer)
    bbox: Mapped[list | None] = mapped_column(JSON, nullable=True)
    raw_metric: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_unit: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    standard_metric_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    standard_metric_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    result_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_numeric: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    comparator: Mapped[str | None] = mapped_column(String(8), nullable=True)
    normalized_unit: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reference_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_low: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    reference_high: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    abnormal: Mapped[str | None] = mapped_column(String(32), nullable=True)
    final_decision: Mapped[str] = mapped_column(String(16))
    review_reasons: Mapped[list] = mapped_column(JSON)
    review_category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    evidence: Mapped[dict] = mapped_column(JSON)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class StandardMetric(Base):
    __tablename__ = "standard_metrics"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class ResultFields:
    """Final candidate/value columns; never used to update a machine snapshot."""

    sequence_no: Mapped[int] = mapped_column(Integer)
    metric_name: Mapped[str] = mapped_column(Text)
    standard_metric_id: Mapped[str | None] = mapped_column(
        ForeignKey("standard_metrics.id"), nullable=True)
    result_text: Mapped[str] = mapped_column(Text)
    result_numeric: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    comparator: Mapped[str | None] = mapped_column(String(8), nullable=True)
    unit_original: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit_normalized: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reference_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_low: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    reference_high: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    abnormal: Mapped[str | None] = mapped_column(String(32), nullable=True)


class ConfirmationItem(ResultFields, Base):
    __tablename__ = "confirmation_items"
    __table_args__ = (UniqueConstraint("ingestion_id", "sequence_no"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    ingestion_id: Mapped[str] = mapped_column(ForeignKey("report_ingestions.id"), index=True)
    source_ocr_result_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("ocr_result_items.id"), unique=True, nullable=True)
    source_type: Mapped[str] = mapped_column(String(16))
    review_status: Mapped[str] = mapped_column(String(16))
    resolution: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class LabReport(Base):
    __tablename__ = "lab_reports"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    health_profile_id: Mapped[str] = mapped_column(ForeignKey("health_profiles.id"), index=True)
    source_ingestion_id: Mapped[str] = mapped_column(ForeignKey("report_ingestions.id"), unique=True)
    hospital_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    examination_date: Mapped[date] = mapped_column(Date, index=True)
    examination_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    report_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    report_category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    has_manual_correction: Mapped[bool] = mapped_column(default=False)
    has_manual_items: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class LabResult(ResultFields, Base):
    __tablename__ = "lab_results"
    __table_args__ = (Index("ix_lab_results_profile_metric_date",
                            "health_profile_id", "standard_metric_id", "examination_date"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    report_id: Mapped[str] = mapped_column(ForeignKey("lab_reports.id"), index=True)
    health_profile_id: Mapped[str] = mapped_column(ForeignKey("health_profiles.id"), index=True)
    source_confirmation_item_id: Mapped[str] = mapped_column(
        ForeignKey("confirmation_items.id"), unique=True)
    data_source: Mapped[str] = mapped_column(String(16))
    examination_date: Mapped[date] = mapped_column(Date, index=True)
    examination_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MetricFavorite(Base):
    __tablename__ = "metric_favorites"
    __table_args__ = (UniqueConstraint(
        "health_profile_id", "standard_metric_id", name="uq_metric_favorites_profile_metric"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    health_profile_id: Mapped[str] = mapped_column(ForeignKey("health_profiles.id"))
    standard_metric_id: Mapped[str] = mapped_column(ForeignKey("standard_metrics.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
