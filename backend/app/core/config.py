from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_ENV,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    database_url: str
    log_level: str = "INFO"
    jwt_secret: str = ""
    admin_username: str = ""
    admin_password_hash: str = ""
    admin_jwt_secret: str = ""
    wechat_app_id: str = ""
    wechat_app_secret: str = ""
    cos_secret_id: str = ""
    cos_secret_key: str = ""
    cos_bucket: str = ""
    cos_region: str = ""
    ocr_work_dir: str = "./runtime/ocr"
    ocr_normal_python: str = ".venv/Scripts/python.exe"
    ocr_paddle_python: str = ".venv-paddle/Scripts/python.exe"
    ocr_page_timeout_seconds: int = 1800
    ocr_task_lease_seconds: int = Field(default=1800, gt=0)
    ocr_worker_concurrency: int = 1


@lru_cache
def get_settings() -> Settings:
    return Settings()
