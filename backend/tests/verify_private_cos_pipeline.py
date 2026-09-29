"""Exercise private COS input and output with a synthetic test image only.

Run from backend with: image-path normal-python paddle-python
Temporary COS keys are deleted in finally; no user asset is touched.
"""

import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app import ocr_pipeline, ocr_worker
from app.core.config import get_settings
from app.core.cos import client as cos_client
from app.models import HealthProfile, OcrResultItem, OcrTask, ReportAsset, ReportIngestion, User
from app.ocr_queue import claim


def verify_worker_persistence(inputs: list[str], image_size: int) -> None:
    """Run the real Worker against a disposable PostgreSQL database and COS objects."""
    original_url = os.environ.get("DATABASE_URL")
    base_url = make_url(get_settings().database_url)
    admin = create_engine(base_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    database_name = "checkup_stage03_full_" + uuid4().hex[:12]
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{database_name}"'))
    test_url = base_url.set(database=database_name)
    os.environ["DATABASE_URL"] = test_url.render_as_string(hide_password=False)
    get_settings.cache_clear()
    engine = None
    try:
        command.upgrade(Config("alembic.ini"), "head")
        engine = create_engine(test_url)
        factory = sessionmaker(engine, expire_on_commit=False)
        ingestion_id = inputs[0].split("/")[3]
        with factory() as db:
            user = User(id="stage03-test", wechat_openid="synthetic-stage03")
            db.add(user)
            db.flush()
            profile = HealthProfile(user_id=user.id, display_name="合成测试", relation="SELF")
            db.add(profile)
            db.flush()
            ingestion = ReportIngestion(id=ingestion_id, user_id=user.id,
                                        health_profile_id=profile.id, status="QUEUED")
            db.add(ingestion)
            db.flush()
            page2 = ReportAsset(ingestion_id=ingestion_id, cos_object_key=inputs[0], page_no=2,
                                mime_type="image/jpeg", file_size=image_size, upload_status="UPLOADED")
            page1 = ReportAsset(ingestion_id=ingestion_id, cos_object_key=inputs[1], page_no=1,
                                mime_type="image/jpeg", file_size=image_size, upload_status="UPLOADED")
            db.add_all([page2, page1])
            db.flush()
            manifest = [
                {"asset_id": page2.id, "page_no": 2, "cos_object_key": inputs[0],
                 "mime_type": "image/jpeg", "file_size": image_size},
                {"asset_id": page1.id, "page_no": 1, "cos_object_key": inputs[1],
                 "mime_type": "image/jpeg", "file_size": image_size},
            ]
            task = OcrTask(ingestion_id=ingestion_id, run_no=1, status="QUEUED",
                           input_manifest=manifest)
            db.add(task)
            db.commit()
            task_id = task.id
        with factory() as db:
            claimed = claim(db, "integration-worker")
            assert claimed.id == task_id
        ocr_worker.process(factory, claimed, "integration-worker")
        with factory() as db:
            task = db.get(OcrTask, task_id)
            items = db.scalars(select(OcrResultItem).where(OcrResultItem.ocr_task_id == task_id)
                               .order_by(OcrResultItem.sequence_no)).all()
            assert task.status == "SUCCEEDED" and task.artifact_root
            assert db.get(ReportIngestion, ingestion_id).status == "PENDING_CONFIRMATION"
            assert len(items) == task.result_summary["total_count"]
            assert {item.page_no for item in items} == {1, 2}
            assert [item.page_no for item in items] == sorted(item.page_no for item in items)
            print(f"PostgreSQL + Worker + private COS: PASS; items={len(items)}")
    finally:
        if engine is not None:
            engine.dispose()
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE "{database_name}" WITH (FORCE)'))
        admin.dispose()
        if original_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original_url
        get_settings.cache_clear()


def main() -> None:
    image_path = Path(sys.argv[1])
    normal_python, paddle_python = sys.argv[2:4]
    cfg = get_settings()
    if not all((cfg.cos_bucket, cfg.cos_region, cfg.cos_secret_id, cfg.cos_secret_key)):
        raise RuntimeError("COS_NOT_CONFIGURED")
    prefix = f"users/stage03-test/ingestions/{uuid4()}/"
    inputs = [prefix + "original/page-2.jpg", prefix + "original/page-1.jpg"]
    uploaded = []
    remote = cos_client()

    class RecordingCos:
        def get_object(self, **kwargs):
            return remote.get_object(**kwargs)

        def put_object(self, **kwargs):
            result = remote.put_object(**kwargs)
            uploaded.append(kwargs["Key"])
            return result

    try:
        for key in inputs:
            with image_path.open("rb") as body:
                remote.put_object(Bucket=cfg.cos_bucket, Key=key, Body=body)
            uploaded.append(key)
        with tempfile.TemporaryDirectory(prefix="stage03-cos-") as directory:
            ocr_pipeline.client = RecordingCos
            ocr_pipeline.get_settings = lambda: SimpleNamespace(
                cos_bucket=cfg.cos_bucket, ocr_work_dir=directory,
                ocr_normal_python=normal_python, ocr_paddle_python=paddle_python,
                ocr_page_timeout_seconds=1800,
            )
            task = SimpleNamespace(
                id="synthetic-cos-task", ingestion_id=prefix.split("/")[3],
                run_no=9, attempt_count=1,
                input_manifest=[
                    {"asset_id": "asset-page-2", "page_no": 2,
                     "cos_object_key": inputs[0], "mime_type": "image/jpeg",
                     "file_size": image_path.stat().st_size},
                    {"asset_id": "asset-page-1", "page_no": 1,
                     "cos_object_key": inputs[1], "mime_type": "image/jpeg",
                     "file_size": image_path.stat().st_size},
                ],
            )
            rows, _, summary, root = ocr_pipeline.run_pipeline(task, "stage03-test")
            pages = [row["page_no"] for row in rows]
            assert pages == sorted(pages) and set(pages) == {1, 2}
            assert summary["total_count"] == len(rows)
            assert root + "manifest.json" in uploaded
            print(f"private COS two-page Pipeline: PASS; rows={len(rows)}; objects={len(uploaded)}")
            verify_worker_persistence(inputs, image_path.stat().st_size)
    finally:
        for key in uploaded:
            remote.delete_object(Bucket=cfg.cos_bucket, Key=key)


if __name__ == "__main__":
    main()
