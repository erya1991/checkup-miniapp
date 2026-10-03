from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import profile_deletion
from app.cleanup_worker import attempt_cleanup
from app.confirmation import ConfirmationError
from app.core.auth import create_token, current_user, db_session, exchange_wechat_code
from app.core.cos import delete_object, object_metadata, preview_url, upload_credential
from app.db.session import create_session_factory
from app.models import (
    FileCleanup,
    HealthProfile,
    OcrTask,
    ReportAsset,
    ReportIngestion,
    UploadAuthorization,
    User,
)
from app.profile_lifecycle import lock_lifecycle

router = APIRouter()
DB_DEP = Depends(db_session)
USER_DEP = Depends(current_user)
RELATIONS = {"SELF", "FATHER", "MOTHER", "SPOUSE", "OTHER"}
GENDERS = {"MALE", "FEMALE", "OTHER"}


def missing(code: str = "RESOURCE_NOT_FOUND") -> None:
    raise HTTPException(404, code)


def profile_for(db: Session, user: User, profile_id: str) -> HealthProfile:
    profile = db.scalar(select(HealthProfile).where(HealthProfile.id == profile_id,
                                                   HealthProfile.user_id == user.id,
                                                   HealthProfile.status == "ACTIVE"))
    if not profile:
        missing("PROFILE_NOT_FOUND")
    return profile


def ingestion_for(db: Session, user: User, ingestion_id: str,
                  lock: bool = False) -> ReportIngestion:
    if lock:
        lock_lifecycle(db, user.id)
    statement = select(ReportIngestion).where(ReportIngestion.id == ingestion_id,
                                              ReportIngestion.user_id == user.id)
    if lock:
        statement = statement.with_for_update().execution_options(populate_existing=True)
    ingestion = db.scalar(statement)
    if not ingestion:
        missing("REPORT_NOT_FOUND")
    return ingestion


def editable_input(ingestion: ReportIngestion) -> None:
    if ingestion.status not in {"UPLOADING", "READY"}:
        raise HTTPException(409, "INGESTION_INPUT_FROZEN")


def profile_data(p: HealthProfile) -> dict:
    return {"id": p.id, "display_name": p.display_name, "relation": p.relation,
            "gender": p.gender, "birth_date": p.birth_date, "status": p.status}


def asset_data(a: ReportAsset) -> dict:
    return {"id": a.id, "page_no": a.page_no, "mime_type": a.mime_type,
            "file_size": a.file_size, "upload_status": a.upload_status}


def ingestion_data(db: Session, i: ReportIngestion) -> dict:
    assets = db.scalars(select(ReportAsset).where(ReportAsset.ingestion_id == i.id)
                        .order_by(ReportAsset.page_no)).all()
    return {"id": i.id, "health_profile_id": i.health_profile_id,
            "mode": i.mode, "status": i.status, "created_at": i.created_at,
            "assets": [asset_data(a) for a in assets]}


class WechatLogin(BaseModel):
    code: str = Field(min_length=1, max_length=256)


@router.post("/auth/wechat")
def login(body: WechatLogin, db: Session = DB_DEP):
    openid = exchange_wechat_code(body.code)
    user = db.scalar(select(User).where(User.wechat_openid == openid))
    if not user:
        user = User(wechat_openid=openid)
        db.add(user)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            user = db.scalar(select(User).where(User.wechat_openid == openid))
            if not user:
                raise
    user.last_login_at = datetime.now(UTC)
    db.commit()
    return {"access_token": create_token(user.id), "token_type": "Bearer",
            "expires_in": 604800, "user": {"id": user.id,
                                            "default_health_profile_id": user.default_health_profile_id}}


@router.get("/me")
def me(user: User = USER_DEP):
    return {"id": user.id, "default_health_profile_id": user.default_health_profile_id}


class ProfileInput(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)
    relation: str
    gender: str | None = None
    birth_date: date | None = None


class ProfilePatch(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    relation: str | None = None
    gender: str | None = None
    birth_date: date | None = None


def validate_profile(relation: str, gender: str | None) -> None:
    if relation not in RELATIONS or (gender is not None and gender not in GENDERS):
        raise HTTPException(422, "INVALID_PROFILE_FIELD")


@router.get("/health-profiles")
def profiles(user: User = USER_DEP, db: Session = DB_DEP):
    return [profile_data(p) for p in db.scalars(select(HealthProfile).where(
        HealthProfile.user_id == user.id, HealthProfile.status == "ACTIVE")
        .order_by(HealthProfile.created_at)).all()]


@router.post("/health-profiles", status_code=201)
def create_profile(body: ProfileInput, user: User = USER_DEP,
                   db: Session = DB_DEP):
    user = lock_lifecycle(db, user.id)
    validate_profile(body.relation, body.gender)
    p = HealthProfile(user_id=user.id, **body.model_dump())
    db.add(p)
    db.flush()
    if not user.default_health_profile_id:
        user.default_health_profile_id = p.id
    db.commit()
    return profile_data(p)


@router.get("/health-profiles/{profile_id}")
def get_profile(profile_id: str, user: User = USER_DEP,
                db: Session = DB_DEP):
    return profile_data(profile_for(db, user, profile_id))


@router.patch("/health-profiles/{profile_id}")
@router.put("/health-profiles/{profile_id}")
def edit_profile(profile_id: str, body: ProfilePatch, user: User = USER_DEP,
                 db: Session = DB_DEP):
    user = lock_lifecycle(db, user.id)
    p = profile_for(db, user, profile_id)
    changes = body.model_dump(exclude_unset=True)
    validate_profile(changes.get("relation", p.relation), changes.get("gender", p.gender))
    for name, value in changes.items():
        setattr(p, name, value)
    db.commit()
    return profile_data(p)


@router.delete("/health-profiles/{profile_id}", status_code=204)
def remove_profile(profile_id: str, user: User = USER_DEP,
                   db: Session = DB_DEP):
    try:
        cleanup_ids = profile_deletion.delete_profile(db, user.id, profile_id)
        db.commit()
    except (HTTPException, ConfirmationError):
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(500, "PROFILE_DELETE_FAILED") from exc
    for cleanup_id in cleanup_ids:
        attempt_cleanup(create_session_factory(db.get_bind()), cleanup_id)


@router.get("/health-profiles/{profile_id}/deletion-impact")
def deletion_impact(profile_id: str, user: User = USER_DEP, db: Session = DB_DEP):
    return profile_deletion.deletion_impact(db, user.id, profile_id)


class DefaultProfile(BaseModel):
    health_profile_id: str


@router.put("/me/default-health-profile")
def set_default(body: DefaultProfile, user: User = USER_DEP,
                db: Session = DB_DEP):
    user = lock_lifecycle(db, user.id)
    profile_for(db, user, body.health_profile_id)
    user.default_health_profile_id = body.health_profile_id
    db.commit()
    return {"default_health_profile_id": user.default_health_profile_id}


class IngestionInput(BaseModel):
    health_profile_id: str
    mode: str = "OCR"


@router.post("/ingestions", status_code=201)
def create_ingestion(body: IngestionInput, user: User = USER_DEP,
                     db: Session = DB_DEP):
    user = lock_lifecycle(db, user.id)
    profile_for(db, user, body.health_profile_id)
    if body.mode != "OCR":
        raise HTTPException(422, "INVALID_INGESTION_MODE")
    i = ReportIngestion(user_id=user.id, health_profile_id=body.health_profile_id,
                        mode="OCR", status="UPLOADING")
    db.add(i)
    db.commit()
    return ingestion_data(db, i)


@router.get("/ingestions")
def list_ingestions(health_profile_id: str | None = None, user: User = USER_DEP,
                    db: Session = DB_DEP):
    statement = select(ReportIngestion).where(ReportIngestion.user_id == user.id)
    if health_profile_id is not None:
        profile_for(db, user, health_profile_id)
        statement = statement.where(ReportIngestion.health_profile_id == health_profile_id)
    rows = db.scalars(statement.order_by(ReportIngestion.created_at.desc(),
                                         ReportIngestion.id.desc())).all()
    result = []
    for ingestion in rows:
        item = ingestion_data(db, ingestion)
        item["result_summary"] = None
        if ingestion.status == "PENDING_CONFIRMATION":
            task = db.scalar(select(OcrTask).where(OcrTask.ingestion_id == ingestion.id,
                                                    OcrTask.status == "SUCCEEDED")
                             .order_by(OcrTask.run_no.desc()).limit(1))
            if task:
                item["result_summary"] = task.result_summary
        result.append(item)
    return result


@router.get("/ingestions/{ingestion_id}")
def get_ingestion(ingestion_id: str, user: User = USER_DEP,
                  db: Session = DB_DEP):
    return ingestion_data(db, ingestion_for(db, user, ingestion_id))


class UploadRequest(BaseModel):
    mime_type: str


@router.post("/ingestions/{ingestion_id}/upload-authorizations")
def authorize_upload(ingestion_id: str, body: UploadRequest,
                     user: User = USER_DEP, db: Session = DB_DEP):
    i = ingestion_for(db, user, ingestion_id, lock=True)
    editable_input(i)
    ext = {"image/jpeg": "jpg", "image/png": "png"}.get(body.mime_type)
    if not ext:
        raise HTTPException(422, "UNSUPPORTED_IMAGE_TYPE")
    key = f"users/{user.id}/ingestions/{ingestion_id}/original/{uuid4()}.{ext}"
    result = upload_credential(key)
    db.add(UploadAuthorization(object_key=key, ingestion_id=ingestion_id,
                               expires_at=max(datetime.now(UTC) + timedelta(minutes=15),
                                              datetime.fromtimestamp(result["expired_time"], UTC))))
    db.commit()
    return result


class AssetInput(BaseModel):
    object_key: str
    mime_type: str
    file_size: int = Field(gt=0, le=20_000_000)


@router.post("/ingestions/{ingestion_id}/assets", status_code=201)
def register_asset(ingestion_id: str, body: AssetInput, user: User = USER_DEP,
                   db: Session = DB_DEP):
    i = ingestion_for(db, user, ingestion_id, lock=True)
    editable_input(i)
    authorization = db.scalar(select(UploadAuthorization).where(
        UploadAuthorization.object_key == body.object_key,
        UploadAuthorization.ingestion_id == i.id))
    if not authorization or authorization.consumed_at:
        raise HTTPException(409, "UPLOAD_AUTHORIZATION_INVALID")
    expiry = authorization.expires_at.replace(tzinfo=UTC)
    if expiry < datetime.now(UTC):
        raise HTTPException(409, "UPLOAD_AUTHORIZATION_EXPIRED")
    expected_mime = "image/jpeg" if body.object_key.endswith(".jpg") else "image/png"
    if body.mime_type != expected_mime:
        raise HTTPException(422, "INVALID_IMAGE_TYPE")
    metadata = object_metadata(body.object_key)
    uploaded_size = next((value for name, value in metadata.items()
                          if name.lower() == "content-length"), -1)
    if int(uploaded_size) != body.file_size:
        raise HTTPException(409, "UPLOAD_SIZE_MISMATCH")
    assets = db.scalars(select(ReportAsset).where(ReportAsset.ingestion_id == i.id)).all()
    asset = ReportAsset(ingestion_id=i.id, cos_object_key=body.object_key,
                        page_no=len(assets) + 1, mime_type=body.mime_type,
                        file_size=body.file_size, upload_status="UPLOADED")
    db.add(asset)
    authorization.consumed_at = datetime.now(UTC)
    i.status = "READY"
    db.commit()
    return asset_data(asset)


class AssetOrder(BaseModel):
    asset_ids: list[str]


@router.put("/ingestions/{ingestion_id}/assets/order")
def reorder_assets(ingestion_id: str, body: AssetOrder, user: User = USER_DEP,
                   db: Session = DB_DEP):
    i = ingestion_for(db, user, ingestion_id, lock=True)
    editable_input(i)
    assets = db.scalars(select(ReportAsset).where(ReportAsset.ingestion_id == i.id)).all()
    if len(body.asset_ids) != len(assets) or set(body.asset_ids) != {a.id for a in assets}:
        raise HTTPException(422, "INVALID_ASSET_ORDER")
    by_id = {a.id: a for a in assets}
    for a in assets:
        a.page_no = -a.page_no
    db.flush()
    for index, asset_id in enumerate(body.asset_ids, 1):
        by_id[asset_id].page_no = index
    db.commit()
    return ingestion_data(db, i)


@router.delete("/ingestions/{ingestion_id}/assets/{asset_id}")
def remove_asset(ingestion_id: str, asset_id: str, user: User = USER_DEP,
                 db: Session = DB_DEP):
    i = ingestion_for(db, user, ingestion_id, lock=True)
    editable_input(i)
    asset = db.scalar(select(ReportAsset).where(ReportAsset.id == asset_id,
                                                ReportAsset.ingestion_id == i.id))
    if not asset:
        missing()
    cleanup = db.scalar(select(FileCleanup).where(FileCleanup.cos_object_key == asset.cos_object_key))
    if not cleanup:
        cleanup = FileCleanup(cos_object_key=asset.cos_object_key, status="PENDING")
        db.add(cleanup)
    db.flush()
    try:
        delete_object(asset.cos_object_key)
    except HTTPException:
        db.commit()  # keep a durable cleanup record and the still-referenced asset
        raise
    cleanup.status = "DONE"
    db.delete(asset)
    db.flush()
    remaining = db.scalars(select(ReportAsset).where(ReportAsset.ingestion_id == i.id)
                           .order_by(ReportAsset.page_no)).all()
    for index, row in enumerate(remaining, 1):
        row.page_no = index
    i.status = "READY" if remaining else "UPLOADING"
    db.commit()
    return ingestion_data(db, i)


@router.get("/ingestions/{ingestion_id}/assets/{asset_id}/preview")
def get_asset_preview(ingestion_id: str, asset_id: str, user: User = USER_DEP,
                      db: Session = DB_DEP):
    i = ingestion_for(db, user, ingestion_id)
    asset = db.scalar(select(ReportAsset).where(ReportAsset.id == asset_id,
                                                ReportAsset.ingestion_id == i.id))
    if not asset:
        missing()
    return {"url": preview_url(asset.cos_object_key), "expires_in": 300}

