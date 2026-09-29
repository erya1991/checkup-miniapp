"""One-shot PostgreSQL 17 queue acceptance in a disposable database.

Run from backend: .venv/Scripts/python.exe tests/verify_postgres_queue.py
"""

import os
from datetime import timedelta
from time import sleep
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import HealthProfile, OcrTask, ReportIngestion, User
from app.ocr_queue import claim, fail, renew, utcnow
from app.ocr_worker import WORKER_LOCK_KEY, heartbeat_interval_seconds


def main() -> None:
    original_env = os.environ.get("DATABASE_URL")
    original_lease_env = os.environ.get("OCR_TASK_LEASE_SECONDS")
    base_url = make_url(get_settings().database_url)
    admin_url = base_url.set(database="postgres")
    name = "checkup_stage03_test_" + uuid4().hex[:12]
    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        version = connection.execute(text("SHOW server_version_num")).scalar_one()
        assert int(version) // 10000 == 17, version
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    test_url = base_url.set(database=name)
    os.environ["DATABASE_URL"] = test_url.render_as_string(hide_password=False)
    os.environ["OCR_TASK_LEASE_SECONDS"] = "2"
    get_settings.cache_clear()
    engine = None
    try:
        command.upgrade(Config("alembic.ini"), "head")
        engine = create_engine(test_url)
        with Session(engine) as db:
            user = User(wechat_openid="stage03-test")
            db.add(user)
            db.flush()
            profile = HealthProfile(user_id=user.id, display_name="测试", relation="SELF")
            db.add(profile)
            db.flush()
            ingestion = ReportIngestion(user_id=user.id, health_profile_id=profile.id, status="QUEUED")
            db.add(ingestion)
            db.flush()
            task = OcrTask(ingestion_id=ingestion.id, run_no=1, status="QUEUED", input_manifest=[])
            db.add(task)
            db.commit()
            task_id = task.id
            ingestion_id = ingestion.id

        # Session A holds the row lock; B must skip the task immediately.
        with Session(engine) as a, Session(engine) as b:
            locked = a.scalar(select(OcrTask).where(OcrTask.id == task_id)
                              .with_for_update(skip_locked=True))
            assert locked is not None
            assert claim(b, "worker-b") is None
            a.rollback()
        print("double-session SKIP LOCKED: PASS")

        with engine.connect() as a, engine.connect() as b:
            assert a.scalar(text("SELECT pg_try_advisory_lock(:key)"),
                            {"key": WORKER_LOCK_KEY})
            assert not b.scalar(text("SELECT pg_try_advisory_lock(:key)"),
                                {"key": WORKER_LOCK_KEY})
            a.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": WORKER_LOCK_KEY})
            assert b.scalar(text("SELECT pg_try_advisory_lock(:key)"),
                            {"key": WORKER_LOCK_KEY})
            b.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": WORKER_LOCK_KEY})
        print("single-Worker advisory lock: PASS")

        # A committed claim and renewal use the configured short lease. After
        # the renewed lease actually expires, another worker reclaims the task.
        with Session(engine) as db:
            first = claim(db, "worker-a")
            assert first.id == task_id and first.attempt_count == 1
            first_expiry = first.lease_expires_at
            assert first_expiry - first.locked_at == timedelta(seconds=2)
            assert heartbeat_interval_seconds() < 2
            assert renew(db, task_id, "worker-a")
            renewed_expiry = db.get(OcrTask, task_id).lease_expires_at
            assert renewed_expiry >= first_expiry
            assert 0 < (renewed_expiry - utcnow()).total_seconds() <= 2
        engine.dispose()
        engine = create_engine(test_url)
        with Session(engine) as db:
            assert db.get(OcrTask, task_id).status == "PROCESSING"
            assert claim(db, "worker-b") is None
        sleep(max(0, (renewed_expiry - utcnow()).total_seconds()) + 0.1)
        with Session(engine) as db:
            second = claim(db, "worker-b")
            assert second.id == task_id and second.attempt_count == 2
            assert db.get(ReportIngestion, ingestion_id).status == "PROCESSING"
            assert fail(db, task_id, "worker-a", "STALE") is False
            assert fail(db, task_id, "worker-b", "OCR_COS_READ_FAILED", recoverable=True)
            assert db.get(OcrTask, task_id).status == "QUEUED"
        print("custom short lease, renewal, and restart recovery: PASS")

        with Session(engine) as db:
            db.add(OcrTask(ingestion_id=ingestion_id, run_no=1, status="QUEUED",
                           input_manifest=[]))
            try:
                db.commit()
                raise AssertionError("duplicate run_no was accepted")
            except IntegrityError:
                db.rollback()
        print("UNIQUE(ingestion_id, run_no): PASS")
        print("PostgreSQL 17 queue integration: PASS")
    finally:
        if engine is not None:
            engine.dispose()
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        admin.dispose()
        if original_env is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original_env
        if original_lease_env is None:
            os.environ.pop("OCR_TASK_LEASE_SECONDS", None)
        else:
            os.environ["OCR_TASK_LEASE_SECONDS"] = original_lease_env
        get_settings.cache_clear()


if __name__ == "__main__":
    main()
