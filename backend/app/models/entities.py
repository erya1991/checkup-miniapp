from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
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
    status: Mapped[str] = mapped_column(String(16), default="UPLOADING")
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
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    cos_object_key: Mapped[str] = mapped_column(String(256), unique=True)
    status: Mapped[str] = mapped_column(String(16), default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
