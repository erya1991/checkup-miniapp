"""PostgreSQL 17 Stage 04 acceptance in two uniquely named disposable databases.

Run from backend: .venv/Scripts/python.exe tests/verify_postgres_confirmation.py
Does not migrate or modify the configured application database.
"""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from threading import Barrier
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, create_engine, event, func, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import sessionmaker

from app.api.v1.business import ingestion_for
from app.confirmation import commit_report, ensure_workspace
from app.core.config import get_settings
from app.models import (
    ConfirmationItem,
    LabReport,
    LabResult,
    OcrResultItem,
    OcrTask,
    ReportIngestion,
    StandardMetric,
    User,
)


def legacy_fixture(engine) -> tuple[str, str, str]:
    """Insert through reflected Stage 03 tables, before Stage 04 columns exist."""
    tables = MetaData()
    tables.reflect(engine)
    user_id, profile_id, ingestion_id, asset_id, task_id = [str(uuid4()) for _ in range(5)]
    timestamp = datetime.now(UTC)
    with engine.begin() as connection:
        connection.execute(tables.tables["users"].insert(), {
            "id": user_id, "wechat_openid": "stage04-synthetic", "status": "ACTIVE",
            "created_at": timestamp, "updated_at": timestamp, "last_login_at": timestamp})
        connection.execute(tables.tables["health_profiles"].insert(), {
            "id": profile_id, "user_id": user_id, "display_name": "合成测试", "relation": "SELF",
            "status": "ACTIVE", "created_at": timestamp, "updated_at": timestamp})
        connection.execute(tables.tables["report_ingestions"].insert(), {
            "id": ingestion_id, "user_id": user_id, "health_profile_id": profile_id,
            "status": "PENDING_CONFIRMATION", "mode": "OCR", "created_at": timestamp, "updated_at": timestamp})
        connection.execute(tables.tables["report_assets"].insert(), {
            "id": asset_id, "ingestion_id": ingestion_id, "cos_object_key": "synthetic/no-cos-access",
            "page_no": 1, "mime_type": "image/jpeg", "file_size": 123, "upload_status": "UPLOADED",
            "created_at": timestamp})
        connection.execute(tables.tables["ocr_tasks"].insert(), {
            "id": task_id, "ingestion_id": ingestion_id, "run_no": 1, "status": "SUCCEEDED",
            "input_manifest": [{"asset_id": asset_id, "page_no": 1}], "result_summary": {"total_count": 2},
            "attempt_count": 1, "created_at": timestamp, "updated_at": timestamp})
        for sequence, decision in enumerate(("FINAL_AUTO", "FINAL_REVIEW"), 1):
            connection.execute(tables.tables["ocr_result_items"].insert(), {
                "id": str(uuid4()), "ocr_task_id": task_id, "sequence_no": sequence,
                "source_asset_id": asset_id, "page_no": 1, "raw_metric": f"合成指标{sequence}",
                "raw_result": "3.1", "result_text": "3.1", "result_numeric": 3.1,
                "standard_metric_code": "ALT" if sequence == 1 else "UNKNOWN",
                "final_decision": decision, "review_reasons": [], "evidence": {}, "payload": {},
                "created_at": timestamp})
    return user_id, ingestion_id, task_id


def assert_unique(db, model, original):
    values = {c.name: getattr(original, c.name) for c in model.__table__.columns}
    values["id"] = str(uuid4())
    try:
        db.execute(model.__table__.insert().values(**values))
        db.commit()
        raise AssertionError(f"{model.__name__} duplicate source was accepted")
    except IntegrityError:
        db.rollback()


def exercise(engine, user_id, ingestion_id, task_id):
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as db:
        before = [{c.name: getattr(row, c.name) for c in OcrResultItem.__table__.columns}
                  for row in db.scalars(select(OcrResultItem).where(OcrResultItem.ocr_task_id == task_id)
                                         .order_by(OcrResultItem.sequence_no))]
        assert db.scalar(select(func.count()).select_from(StandardMetric)) == 12
    barrier = Barrier(2)

    def initialize():
        with factory() as db:
            user = db.get(User, user_id)
            barrier.wait(timeout=15)
            ingestion = ingestion_for(db, user, ingestion_id, lock=True)
            items = ensure_workspace(db, ingestion)
            ids = [i.id for i in items]
            db.commit()
            return ids

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(initialize) for _ in range(2)]
        ids = [future.result(timeout=30) for future in futures]
    assert ids[0] == ids[1] and len(ids[0]) == 2
    print("Stage 03 upgrade preserves old task; concurrent initialization and source UNIQUE: PASS")
    with factory() as db:
        ingestion = ingestion_for(db, db.get(User, user_id), ingestion_id, lock=True)
        ingestion.examination_date = date(2026, 8, 1)
        for item in ensure_workspace(db, ingestion):
            if item.review_status == "PENDING":
                item.review_status, item.resolution = "RESOLVED", "KEEP_ORIGINAL_NAME"
        db.commit()

    # Real PostgreSQL error after a report/first result is flushed: the entire
    # database transaction, including ingestion state, must roll back.
    calls = 0

    def abort_second(_mapper, connection, _target):
        nonlocal calls
        calls += 1
        if calls == 2:
            connection.exec_driver_sql("SELECT 1 / 0")

    event.listen(LabResult, "before_insert", abort_second)
    try:
        with factory() as db:
            try:
                row = ingestion_for(db, db.get(User, user_id), ingestion_id, lock=True)
                commit_report(db, row)
                db.commit()
                raise AssertionError("injected PostgreSQL error did not abort commit")
            except DBAPIError:
                db.rollback()
    finally:
        event.remove(LabResult, "before_insert", abort_second)
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(LabReport)) == 0
        assert db.scalar(select(func.count()).select_from(LabResult)) == 0
        assert db.get(ReportIngestion, ingestion_id).status == "PENDING_CONFIRMATION"
        assert db.get(ReportIngestion, ingestion_id).confirmed_at is None
    print("PostgreSQL transaction rollback after partial flush: PASS")

    barrier = Barrier(2)

    def commit():
        with factory() as db:
            user = db.get(User, user_id)
            barrier.wait(timeout=15)
            ingestion = ingestion_for(db, user, ingestion_id, lock=True)
            report = commit_report(db, ingestion)
            db.commit()
            return report.id

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(commit) for _ in range(2)]
        ids = [future.result(timeout=30) for future in futures]
    assert ids[0] == ids[1]
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(LabReport)) == 1
        assert db.scalar(select(func.count()).select_from(LabResult)) == 2
        ingestion = ingestion_for(db, db.get(User, user_id), ingestion_id, lock=True)
        assert commit_report(db, ingestion).id == ids[0]
        assert ingestion.status == "CONFIRMED" and ingestion.confirmed_at is not None
        db.commit()
    print("two independent sessions concurrent commit + timeout retry: PASS")

    with factory() as db:
        report = db.get(LabReport, ids[0])
        assert report.examination_date == date(2026, 8, 1)
        assert_unique(db, LabReport, report)
        result = db.scalar(select(LabResult))
        assert_unique(db, LabResult, result)
        item = db.scalar(select(ConfirmationItem).where(ConfirmationItem.source_ocr_result_item_id.is_not(None)))
        values = {c.name: getattr(item, c.name) for c in ConfirmationItem.__table__.columns}
        values.update(id=str(uuid4()), sequence_no=100)
        try:
            db.execute(ConfirmationItem.__table__.insert().values(**values))
            db.commit()
            raise AssertionError("duplicate source OCR accepted")
        except IntegrityError:
            db.rollback()
        after = [{c.name: getattr(row, c.name) for c in OcrResultItem.__table__.columns}
                 for row in db.scalars(select(OcrResultItem).where(OcrResultItem.ocr_task_id == task_id)
                                        .order_by(OcrResultItem.sequence_no))]
        assert before == after
        assert db.get(OcrTask, task_id).status == "SUCCEEDED"
    print("database source uniqueness x3; OCR immutable; formal date and trace: PASS")
    schema = inspect(engine)
    for table in ("confirmation_items", "lab_reports", "lab_results"):
        assert schema.get_foreign_keys(table) and schema.get_indexes(table)


def main():
    original_env = os.environ.get("DATABASE_URL")
    base_url = make_url(get_settings().database_url)
    admin = create_engine(base_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    names = ["checkup_stage04_" + suffix + "_" + uuid4().hex[:12] for suffix in ("upgrade", "clean")]
    created = []
    engines = []
    try:
        with admin.connect() as connection:
            assert int(connection.scalar(text("SHOW server_version_num"))) // 10000 == 17
        for index, name in enumerate(names):
            with admin.connect() as connection:
                connection.execute(text(f'CREATE DATABASE "{name}"'))
            created.append(name)
            url = base_url.set(database=name)
            os.environ["DATABASE_URL"] = url.render_as_string(hide_password=False)
            get_settings.cache_clear()
            engine = create_engine(url)
            engines.append(engine)
            if index == 0:
                command.upgrade(Config("alembic.ini"), "0003_ocr")
                user_id, ingestion_id, task_id = legacy_fixture(engine)
                command.upgrade(Config("alembic.ini"), "head")
                exercise(engine, user_id, ingestion_id, task_id)
            else:
                command.upgrade(Config("alembic.ini"), "head")
            with engine.connect() as connection:
                assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0004_confirmation_report"
            print(("0003 -> 0004" if index == 0 else "empty -> 0001 -> 0002 -> 0003 -> 0004") + " migration: PASS")
        print("PostgreSQL 17 Stage 04 integration: PASS")
    finally:
        for engine in engines:
            engine.dispose()
        # Names come only from this run's fixed prefix + uuid, never user data.
        with admin.connect() as connection:
            for name in created:
                assert name.startswith("checkup_stage04_") and name in names
                connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        admin.dispose()
        if original_env is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original_env
        get_settings.cache_clear()
        print(f"temporary databases removed: {len(created)}")


if __name__ == "__main__":
    main()
