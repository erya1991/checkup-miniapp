"""Independent, environment-configured single-admin authentication."""
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Header, HTTPException

from app.core.config import get_settings


def password_hash(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 600_000)
    return f"pbkdf2_sha256$600000${salt}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, digest = encoded.split("$")
        if algorithm != "pbkdf2_sha256" or not 600_000 <= int(iterations) <= 2_000_000:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations))
        return hmac.compare_digest(actual, bytes.fromhex(digest))
    except (ValueError, TypeError):
        return False


def configured():
    cfg = get_settings()
    if (not cfg.admin_username or not cfg.admin_password_hash or len(cfg.admin_jwt_secret) < 32
            or cfg.admin_jwt_secret == cfg.jwt_secret):
        raise HTTPException(503, "ADMIN_AUTH_NOT_CONFIGURED")
    return cfg


def login(username: str, password: str):
    cfg = configured()
    valid = verify_password(password, cfg.admin_password_hash)
    if not valid or not hmac.compare_digest(username.encode(), cfg.admin_username.encode()):
        raise HTTPException(401, "ADMIN_AUTH_INVALID")
    current = datetime.now(UTC)
    token = jwt.encode({"sub": cfg.admin_username, "scope": "admin", "aud": "checkup-admin",
                        "iat": current, "exp": current + timedelta(hours=8)},
                       cfg.admin_jwt_secret, algorithm="HS256")
    return {"access_token": token, "token_type": "bearer", "expires_in": 28800}


def current_admin(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "ADMIN_AUTH_REQUIRED")
    cfg = configured()
    try:
        payload = jwt.decode(authorization[7:], cfg.admin_jwt_secret, algorithms=["HS256"],
                             audience="checkup-admin", options={"require": ["sub", "exp", "iat", "scope"]})
        if payload["scope"] != "admin" or payload["sub"] != cfg.admin_username:
            raise jwt.InvalidTokenError()
    except jwt.PyJWTError as exc:
        raise HTTPException(401, "ADMIN_AUTH_INVALID") from exc
    return cfg.admin_username
