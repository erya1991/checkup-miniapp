"""Stage 07 PostgreSQL 17 verification in UUID-scoped disposable databases only."""
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from threading import Barrier, Event
from uuid import uuid4

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from verify_postgres_confirmation import legacy_fixture
from verify_postgres_metrics import legacy_reports
from verify_postgres_reports import pending

from app import admin_metrics, admin_ocr, profile_metrics
from app.confirmation import ConfirmationError, commit_report, ensure_workspace
from app.core.config import get_settings
from app.db.base import Base
from app.models import (
    ConfirmationItem,
    LabReport,
    LabResult,
    MetricAlias,
    MetricFavorite,
    OcrResultItem,
    OcrTask,
    ReportIngestion,
    StandardMetric,
    User,
)
from app.ocr_pipeline import map_row


def snapshot(factory):
    with factory() as db:
        return {entity.__tablename__: [
            {c.name: getattr(row, c.name) for c in entity.__table__.columns}
            for row in db.scalars(select(entity).order_by(entity.id))]
            for entity in (OcrTask, OcrResultItem, ConfirmationItem, LabReport, LabResult, MetricFavorite)}


def schema_drift(engine):
    with engine.connect() as conn:
        differences = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert all(len(diff) == 2 and diff[0] in {"add_index", "remove_index"} for diff in differences), differences
    signature = sorted((action, item.table.name, item.name, tuple(c.name for c in item.columns))
                       for action, item in differences)
    assert signature == [
        ("add_index", "ocr_tasks", "ix_ocr_tasks_status", ("status",)),
        ("remove_index", "ocr_tasks", "ix_ocr_tasks_queue", ("status", "next_attempt_at")),
    ], signature
    return signature


def concurrent(factory, operations):
    barrier = Barrier(len(operations))
    def run(operation):
        with factory() as db:
            barrier.wait(timeout=10)
            try:
                result = operation(db)
                db.commit()
                return "SUCCESS", result.id
            except ConfirmationError as exc:
                db.rollback()
                return exc.code, None
    with ThreadPoolExecutor(max_workers=len(operations)) as pool:
        futures = [pool.submit(run, op) for op in operations]
        return [future.result(timeout=20) for future in futures]


def expect_integrity(factory, entity, values):
    with factory() as db:
        db.add(entity(**values))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        else:
            raise AssertionError("PostgreSQL uniqueness not enforced")


def exercise(engine, context):
    factory = sessionmaker(engine, expire_on_commit=False)
    uid, _, profile_id, _, wbc, alt, *_ = context
    before = snapshot(factory)
    with factory() as db:
        ast = db.scalar(select(StandardMetric.id).where(StandardMetric.code == "AST"))
        assert db.scalar(select(func.count()).select_from(StandardMetric)) == 12
        assert db.scalar(select(func.count()).select_from(MetricAlias)) == 0
        assert all(m.category is None for m in db.scalars(select(StandardMetric)))
    codes = concurrent(factory, [lambda db: admin_metrics.create_metric(db, {"code": "RACE07", "name": "并发指标"})] * 2)
    assert sorted(result[0] for result in codes) == ["STANDARD_METRIC_CODE_CONFLICT", "SUCCESS"]
    expect_integrity(factory, StandardMetric, {"code": "RACE07", "name": "直接重复"})
    print("PG004 concurrent code creation + actual database UNIQUE: PASS")

    values = {"standard_metric_id": alt, "alias": " ＊Ｒａｃｅ-Ａｌｉａｓ ", "alias_type": "OCR_VARIANT"}
    aliases = concurrent(factory, [lambda db: admin_metrics.save_alias(db, values),
                                   lambda db: admin_metrics.save_alias(db, {**values, "alias": "race.alias"})])
    assert sorted(result[0] for result in aliases) == ["METRIC_ALIAS_DUPLICATE", "SUCCESS"]
    expect_integrity(factory, MetricAlias, {**values, "normalized_alias": "racealias", "status": "ACTIVE"})
    with factory() as db:
        # Partial uniqueness permits inactive history, not a second ACTIVE identity.
        db.add(MetricAlias(**values, normalized_alias="racealias", status="INACTIVE"))
        db.commit()
    print("PG005/PG006 ACTIVE partial uniqueness, direct writes and concurrent normalized aliases: PASS")

    races = concurrent(factory, [
        lambda db: admin_metrics.save_alias(db, {"standard_metric_id": alt, "alias": "竞态命名", "alias_type": "SYNONYM"}),
        lambda db: admin_metrics.update_metric(db, ast, {"name": "竞态命名"}),
    ])
    assert sorted(result[0] for result in races) == ["METRIC_ALIAS_CONFLICT", "SUCCESS"]
    with factory() as db:
        collision = db.scalar(select(MetricAlias).where(MetricAlias.normalized_alias == "竞态命名"))
        if collision:
            admin_metrics.save_alias(db, {"status": "INACTIVE"}, collision.id)
        else:
            admin_metrics.update_metric(db, ast, {"name": "天门冬氨酸氨基转移酶"})
        for operation in (
            lambda: admin_metrics.save_alias(db, {"standard_metric_id": alt, "alias": "ＡＳＴ", "alias_type": "ABBREVIATION"}),
            lambda: admin_metrics.update_metric(db, ast, {"name": "race.alias"}),
            lambda: admin_metrics.create_metric(db, {"code": "NAMESPACE07", "name": "racealias"}),
        ):
            try:
                operation()
            except ConfirmationError as exc:
                assert exc.code == "METRIC_ALIAS_CONFLICT"
                db.rollback()
            else:
                raise AssertionError("namespace conflict accepted")
        metric = admin_metrics.create_metric(db, {"code": "RESTORE07", "name": "恢复测试"})
        target_id = metric.id
        admin_metrics.update_metric(db, target_id, {"status": "INACTIVE"})
        admin_metrics.save_alias(db, {"standard_metric_id": alt, "alias": "RESTORE07", "alias_type": "SYNONYM"})
        db.commit()
        try:
            admin_metrics.update_metric(db, target_id, {"status": "ACTIVE"})
        except ConfirmationError as exc:
            assert exc.code == "METRIC_ALIAS_CONFLICT"
            db.rollback()
        else:
            raise AssertionError("restore namespace collision accepted")
    print("PG007 bidirectional namespace, restore and alias-vs-rename concurrency: PASS")

    iid = pending(factory, uid, profile_id, report_no="stage07-pending")
    with factory() as db:
        item = db.scalar(select(ConfirmationItem).where(ConfirmationItem.ingestion_id == iid))
        item.standard_metric_id = alt
        db.commit()
        try:
            admin_metrics.update_metric(db, alt, {"status": "INACTIVE"})
        except ConfirmationError as exc:
            assert exc.code == "STANDARD_METRIC_IN_USE_BY_PENDING_CONFIRMATION"
            assert exc.details == {"pending_count": 1}
            db.rollback()
        else:
            raise AssertionError("pending workspace not protected")

    def commit_pending(db):
        ingestion = db.scalar(select(ReportIngestion).where(ReportIngestion.id == iid).with_for_update())
        return commit_report(db, ingestion)
    outcomes = concurrent(factory, [commit_pending, lambda db: admin_metrics.update_metric(db, alt, {"status": "INACTIVE"})])
    assert outcomes[0][0] == "SUCCESS"
    assert outcomes[1][0] in {"SUCCESS", "STANDARD_METRIC_IN_USE_BY_PENDING_CONFIRMATION"}
    with factory() as db:
        assert db.get(ReportIngestion, iid).status == "CONFIRMED"
        assert db.scalar(select(LabResult).where(LabResult.report_id == outcomes[0][1])).standard_metric_id == alt
        admin_metrics.update_metric(db, alt, {"status": "ACTIVE"})
        db.commit()
    print("PG008 pending protection and commit-vs-deactivate are transactional: PASS")

    # Deterministic overlap: the resolver holds shared row locks before the admin
    # attempts deactivate; after initialization commits the admin must see pending.
    _user_id, ocr_iid, task_id = legacy_fixture(engine)
    with factory() as db:
        task = db.get(OcrTask, task_id)
        candidate = {"metricId": "ALT", "standardName": "丙氨酸氨基转移酶"}
        raw = {"raw": {"metric": "合成陌生适配指标"}, "finalStatus": "FINAL_REVIEW",
               "metricMatch": {"status": "UNMATCHED", "metric": candidate,
                               "topCandidates": [{"metric": candidate}]}}
        db.add(OcrResultItem(ocr_task_id=task_id, **map_row(raw, task.input_manifest[0], 3)))
        task.result_summary = {"total_count": 3, "auto_count": 1, "review_count": 2}
        db.commit()
        row = db.scalar(select(OcrResultItem).where(OcrResultItem.ocr_task_id == task_id,
                                                   OcrResultItem.sequence_no == 3))
        assert row.standard_metric_code is None and row.standard_metric_name is None
        assert row.payload == raw and row.evidence["metricMatch"] == raw["metricMatch"]
        issues = admin_ocr.metric_issues(db, issue_type="UNMATCHED_NAME")["items"]
        issue = next(i for i in issues if i["representative_name"] == "合成陌生适配指标")
        assert issue["occurrence_count"] == issue["ingestion_count"] == 1
    print("PG adapter UNMATCHED candidate stored as NULL identity with audit evidence; issue visible: PASS")
    initialized, release, admin_started = Event(), Event(), Event()
    def initialize():
        with factory() as db:
            ingestion = db.scalar(select(ReportIngestion).where(ReportIngestion.id == ocr_iid).with_for_update())
            ensure_workspace(db, ingestion)
            initialized.set()
            assert release.wait(timeout=10)
            db.commit()
    def deactivate():
        with factory() as db:
            admin_started.set()
            try:
                admin_metrics.update_metric(db, alt, {"status": "INACTIVE"})
                db.commit()
            except ConfirmationError as exc:
                db.rollback()
                return exc.code
            return "SUCCESS"
    with ThreadPoolExecutor(max_workers=2) as pool:
        init_future = pool.submit(initialize)
        assert initialized.wait(timeout=10)
        deactivate_future = pool.submit(deactivate)
        assert admin_started.wait(timeout=10)
        try:
            deactivate_future.result(timeout=0.2)
            raise AssertionError("deactivate bypassed resolver row locks")
        except TimeoutError:
            pass
        finally:
            release.set()
        init_future.result(timeout=10)
        assert deactivate_future.result(timeout=10) == "STANDARD_METRIC_IN_USE_BY_PENDING_CONFIRMATION"
    print("PG008 new Confirmation initialization-vs-deactivate row lock protection: PASS")

    with factory() as db:
        old_items = [{c.name: getattr(i, c.name) for c in ConfirmationItem.__table__.columns}
                     for i in db.scalars(select(ConfirmationItem).where(ConfirmationItem.ingestion_id == ocr_iid))]
        ocr_before = [{c.name: getattr(i, c.name) for c in OcrResultItem.__table__.columns}
                      for i in db.scalars(select(OcrResultItem).where(OcrResultItem.ocr_task_id == task_id))]
        admin_metrics.save_alias(db, {"standard_metric_id": alt, "alias": "合成指标2", "alias_type": "OCR_VARIANT"})
        admin_metrics.save_alias(db, {"standard_metric_id": alt, "alias": "合成陌生适配指标", "alias_type": "OCR_VARIANT"})
        db.commit()
        again = ensure_workspace(db, db.get(ReportIngestion, ocr_iid))
        unmatched = next(i for i in again if i.source_ocr_result_item_id == row.id)
        assert unmatched.standard_metric_id is None and unmatched.review_status == "PENDING"
        assert not any(i["representative_name"] == "合成陌生适配指标"
                       for i in admin_ocr.metric_issues(db, issue_type="UNMATCHED_NAME")["items"])
        assert [{c.name: getattr(i, c.name) for c in ConfirmationItem.__table__.columns} for i in again] == old_items
        assert [{c.name: getattr(i, c.name) for c in OcrResultItem.__table__.columns}
                for i in db.scalars(select(OcrResultItem).where(OcrResultItem.ocr_task_id == task_id))] == ocr_before
        assert all("result_text" not in issue for issue in admin_ocr.metric_issues(db)["items"])
    print("PG exact/issue queries leave existing workspace and OCR snapshots unchanged: PASS")

    with factory() as db:
        user = db.get(User, uid)
        original_history = profile_metrics.history(db, user, profile_id, wbc)
        original_trend = profile_metrics.trend(db, user, profile_id, wbc)
        profile_metrics.set_favorite(db, user, profile_id, wbc, True)
        db.commit()
        admin_metrics.update_metric(db, wbc, {"name": "当前白细胞名称", "status": "INACTIVE"})
        db.commit()
        assert profile_metrics.detail(db, user, profile_id, wbc)["standard_metric"]["name"] == "当前白细胞名称"
        assert profile_metrics.detail(db, user, profile_id, wbc)["is_favorite"]
        assert profile_metrics.history(db, user, profile_id, wbc) == original_history
        assert profile_metrics.trend(db, user, profile_id, wbc)["series"] == original_trend["series"]
    after = snapshot(factory)
    old_ids = {row["id"] for row in before["lab_results"]}
    assert [row for row in after["lab_results"] if row["id"] in old_ids] == before["lab_results"]
    print("PG Stage 06 rename/inactive history/trend/favorite, old NULL identities and formal snapshots preserved: PASS")


def main():
    original_env = os.environ.get("DATABASE_URL")
    base_url = make_url(get_settings().database_url)
    admin = create_engine(base_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    names = ["checkup_stage07_" + kind + "_" + uuid4().hex[:12] for kind in ("upgrade", "clean")]
    created, engines = [], []
    try:
        with admin.connect() as conn:
            assert int(conn.scalar(text("SHOW server_version_num"))) // 10000 == 17
        for index, name in enumerate(names):
            with admin.connect() as conn:
                conn.execute(text(f'CREATE DATABASE "{name}"'))
            created.append(name)
            url = base_url.set(database=name)
            os.environ["DATABASE_URL"] = url.render_as_string(hide_password=False)
            get_settings.cache_clear()
            engine = create_engine(url)
            engines.append(engine)
            factory = sessionmaker(engine, expire_on_commit=False)
            if index == 0:
                command.upgrade(Config("alembic.ini"), "0006_metric_trend")
                context = legacy_reports(engine)
                before = snapshot(factory)
                assert not inspect(engine).has_table("metric_aliases")
                assert "category" not in {c["name"] for c in inspect(engine).get_columns("standard_metrics")}
                command.upgrade(Config("alembic.ini"), "head")
                assert snapshot(factory) == before
                print("PG002 0006 -> 0007, all legacy OCR/confirmation/formal/favorite snapshots preserved: PASS")
            else:
                command.upgrade(Config("alembic.ini"), "head")
                context = legacy_reports(engine)
                print("PG001 empty -> 0001..0007: PASS")
            with engine.connect() as conn:
                assert conn.scalar(text("SELECT version_num FROM alembic_version")) == "0007_standard_metric_admin"
            inspector = inspect(engine)
            assert {c["name"] for c in inspector.get_columns("metric_aliases")} == {
                "id", "standard_metric_id", "alias", "normalized_alias", "alias_type", "status", "created_at", "updated_at"}
            assert inspector.get_foreign_keys("metric_aliases")
            assert any(i["name"] == "uq_metric_aliases_active_normalized" and i["unique"]
                       for i in inspector.get_indexes("metric_aliases"))
            schema_drift(engine)
            if index == 0:
                saved = snapshot(factory)
                command.downgrade(Config("alembic.ini"), "0006_metric_trend")
                assert not inspect(engine).has_table("metric_aliases")
                assert "category" not in {c["name"] for c in inspect(engine).get_columns("standard_metrics")}
                assert snapshot(factory) == saved
                command.upgrade(Config("alembic.ini"), "head")
                assert snapshot(factory) == saved
                schema_drift(engine)
                print("PG003 downgrade 0006 / re-upgrade 0007, no medical backfill: PASS")
            exercise(engine, context)
            schema_drift(engine)
        print("PostgreSQL 17 Stage 07 integration: PASS; Stage 03 index drift unchanged")
    finally:
        for engine in engines:
            engine.dispose()
        with admin.connect() as conn:
            for name in created:
                assert name in names and name.startswith("checkup_stage07_")
                conn.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
            assert not conn.execute(text("SELECT datname FROM pg_database WHERE datname = ANY(:names)"), {"names": names}).all()
        admin.dispose()
        if original_env is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original_env
        get_settings.cache_clear()
        print(f"PG009 temporary databases removed and absence verified: {len(created)}")


if __name__ == "__main__":
    main()
