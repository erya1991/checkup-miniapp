import logging
from datetime import UTC, datetime, timedelta
from functools import lru_cache

import httpx
import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import create_db_engine, create_session_factory
from app.models import User

logger = logging.getLogger(__name__)


@lru_cache
def database_factory():
    return create_session_factory(create_db_engine())


def db_session():
    session = database_factory()()
    try:
        yield session
    finally:
        session.close()


def exchange_wechat_code(code: str) -> str:
    cfg = get_settings()
    if not cfg.wechat_app_id or not cfg.wechat_app_secret:
        raise HTTPException(503, "WECHAT_NOT_CONFIGURED")
    try:
        response = httpx.get(
            "https://api.weixin.qq.com/sns/jscode2session",
            params={"appid": cfg.wechat_app_id, "secret": cfg.wechat_app_secret,
                    "js_code": code, "grant_type": "authorization_code"}, timeout=8,
        )
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, "WECHAT_UNAVAILABLE") from exc
    errcode = data.get("errcode")
    if errcode is not None and errcode != 0:
        logger.warning("wechat_code_exchange_failed errcode=%s errmsg=%s", errcode,
                       data.get("errmsg"))
    if not data.get("openid"):
        raise HTTPException(401, "WECHAT_CODE_INVALID")
    return str(data["openid"])


def create_token(user_id: str) -> str:
    secret = get_settings().jwt_secret
    if len(secret) < 32:
        raise HTTPException(503, "TOKEN_SECRET_NOT_CONFIGURED")
    return jwt.encode(
        {"sub": user_id, "exp": datetime.now(UTC) + timedelta(days=7)},
        secret, algorithm="HS256",
    )


DB_DEP = Depends(db_session)

def current_user(authorization: str | None = Header(default=None),
                 db: Session = DB_DEP) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "AUTH_REQUIRED")
    try:
        payload = jwt.decode(authorization[7:], get_settings().jwt_secret, algorithms=["HS256"])
        if payload.get("scope") == "admin":
            raise jwt.InvalidTokenError()
        user = db.scalar(select(User).where(User.id == payload["sub"], User.status == "ACTIVE"))
    except (jwt.PyJWTError, KeyError):
        user = None
    if not user:
        raise HTTPException(401, "AUTH_REQUIRED")
    return user

