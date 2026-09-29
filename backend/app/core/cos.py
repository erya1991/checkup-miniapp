
from fastapi import HTTPException
from qcloud_cos import CosConfig, CosS3Client
from sts.sts import Sts

from app.core.config import get_settings


def client() -> CosS3Client:
    cfg = get_settings()
    if not all((cfg.cos_secret_id, cfg.cos_secret_key, cfg.cos_bucket, cfg.cos_region)):
        raise HTTPException(503, "COS_NOT_CONFIGURED")
    return CosS3Client(CosConfig(Region=cfg.cos_region, SecretId=cfg.cos_secret_id,
                                 SecretKey=cfg.cos_secret_key))


def upload_credential(key: str) -> dict:
    cfg = get_settings()
    if not all((cfg.cos_secret_id, cfg.cos_secret_key, cfg.cos_bucket, cfg.cos_region)):
        raise HTTPException(503, "COS_NOT_CONFIGURED")
    try:
        result = Sts({"secret_id": cfg.cos_secret_id, "secret_key": cfg.cos_secret_key,
                      "bucket": cfg.cos_bucket, "region": cfg.cos_region,
                      "duration_seconds": 900, "allow_prefix": key,
                      "allow_actions": ["name/cos:PutObject"]}).get_credential()
    except Exception as exc:
        raise HTTPException(502, "COS_AUTHORIZATION_FAILED") from exc
    return {"credentials": result["credentials"], "start_time": result["startTime"],
            "expired_time": result["expiredTime"], "bucket": cfg.cos_bucket,
            "region": cfg.cos_region, "object_key": key}


def object_metadata(key: str) -> dict:
    try:
        return client().head_object(Bucket=get_settings().cos_bucket, Key=key)
    except Exception as exc:
        raise HTTPException(409, "UPLOAD_NOT_FOUND") from exc


def delete_object(key: str) -> None:
    try:
        client().delete_object(Bucket=get_settings().cos_bucket, Key=key)
    except Exception as exc:
        raise HTTPException(502, "COS_DELETE_FAILED") from exc


def preview_url(key: str) -> str:
    return client().get_presigned_download_url(Bucket=get_settings().cos_bucket,
                                                Key=key, Expired=300)
