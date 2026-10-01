"""Single-admin master-data APIs and read-only OCR diagnostics."""
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import admin_metrics, admin_ocr
from app.api.v1.confirmation import transaction
from app.confirmation import ConfirmationError
from app.core.admin_auth import current_admin, login
from app.core.auth import db_session

router = APIRouter(prefix="/admin")
ADMIN_DEP = Depends(current_admin)
DB_DEP = Depends(db_session)
Status = Literal["ACTIVE", "INACTIVE"]
AliasType = Literal["SYNONYM", "ABBREVIATION", "OCR_VARIANT", "HOSPITAL_NAME"]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginInput(Input):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=2048)


class MetricInput(Input):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=256)
    category: str | None = Field(default=None, max_length=80)


class MetricPatch(Input):
    code: Any = None  # Presence is explicitly rejected, including null or the current code.
    name: str | None = Field(default=None, max_length=256)
    category: str | None = Field(default=None, max_length=80)
    status: Status | None = None


class AliasInput(Input):
    standard_metric_id: str = Field(min_length=1, max_length=36)
    alias: str = Field(min_length=1, max_length=256)
    alias_type: AliasType


class AliasPatch(Input):
    standard_metric_id: Any = None
    alias: str | None = Field(default=None, max_length=256)
    alias_type: AliasType | None = None
    status: Status | None = None


@router.post("/auth/login")
def auth_login(body: LoginInput):
    return login(body.username, body.password)


@router.get("/me")
def me(admin: str = ADMIN_DEP):
    return {"username": admin, "scope": "admin"}


@router.get("/standard-metrics")
def metrics(q: str = Query(default="", max_length=256), status: Status | None = None,
            category: str | None = Query(default=None, max_length=80),
            page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100),
            admin: str = ADMIN_DEP, db: Session = DB_DEP):
    return admin_metrics.list_metrics(db, q, status, category, page, page_size)


def write(db, operation, serialize, conflict):
    try:
        with transaction(db):
            return serialize(db, operation())
    except IntegrityError as exc:
        raise ConfirmationError(conflict) from exc


@router.post("/standard-metrics", status_code=201)
def create_metric(body: MetricInput, admin: str = ADMIN_DEP, db: Session = DB_DEP):
    return write(db, lambda: admin_metrics.create_metric(db, body.model_dump()),
                 admin_metrics.metric_data, "STANDARD_METRIC_CODE_CONFLICT")


@router.get("/standard-metrics/{metric_id}")
def metric(metric_id: str, admin: str = ADMIN_DEP, db: Session = DB_DEP):
    return admin_metrics.metric_data(db, admin_metrics.metric_for(db, metric_id))


@router.patch("/standard-metrics/{metric_id}")
def patch_metric(metric_id: str, body: MetricPatch, admin: str = ADMIN_DEP, db: Session = DB_DEP):
    return write(db, lambda: admin_metrics.update_metric(db, metric_id, body.model_dump(exclude_unset=True)),
                 admin_metrics.metric_data, "STANDARD_METRIC_CODE_CONFLICT")


@router.get("/metric-aliases")
def aliases(q: str = Query(default="", max_length=256), status: Status | None = None,
            standard_metric_id: str | None = Query(default=None, max_length=36),
            page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100),
            admin: str = ADMIN_DEP, db: Session = DB_DEP):
    return admin_metrics.list_aliases(db, q, status, standard_metric_id, page, page_size)


@router.post("/metric-aliases", status_code=201)
def create_alias(body: AliasInput, admin: str = ADMIN_DEP, db: Session = DB_DEP):
    return write(db, lambda: admin_metrics.save_alias(db, body.model_dump()),
                 admin_metrics.alias_data, "METRIC_ALIAS_DUPLICATE")


@router.patch("/metric-aliases/{alias_id}")
def patch_alias(alias_id: str, body: AliasPatch, admin: str = ADMIN_DEP, db: Session = DB_DEP):
    return write(db, lambda: admin_metrics.save_alias(db, body.model_dump(exclude_unset=True), alias_id),
                 admin_metrics.alias_data, "METRIC_ALIAS_DUPLICATE")


@router.get("/ocr-metric-issues")
def issues(issue_type: Literal["UNMATCHED_NAME", "PRODUCT_METRIC_MISSING", "PRODUCT_METRIC_INACTIVE"] | None = None,
           page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100),
           admin: str = ADMIN_DEP, db: Session = DB_DEP):
    return admin_ocr.metric_issues(db, issue_type, page, page_size)


@router.get("/ocr-tasks")
def tasks(status: Literal["QUEUED", "PROCESSING", "SUCCEEDED", "FAILED"] | None = None,
          pipeline_version: str | None = Query(default=None, max_length=128),
          page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100),
          admin: str = ADMIN_DEP, db: Session = DB_DEP):
    return admin_ocr.tasks(db, status, pipeline_version, page, page_size)
