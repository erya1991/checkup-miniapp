"""Stage 06 acceptance in UUID-named PostgreSQL 17 temporary databases only."""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, time
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import MetaData, create_engine, func, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from verify_postgres_reports import commit, pending

from app import profile_metrics as metrics
from app import reports
from app.confirmation import ConfirmationError
from app.core import auth
from app.core.config import get_settings
from app.db.base import Base
from app.main import app
from app.models import (
    ConfirmationItem,
    HealthProfile,
    LabResult,
    MetricFavorite,
    ReportIngestion,
    StandardMetric,
    User,
)


def formal(factory, user_id, profile_id, entries, examination_date, examination_time=None):
    iid = pending(factory, user_id, profile_id, report_no=str(uuid4()))
    with factory() as db:
        ingestion = db.get(ReportIngestion, iid)
        ingestion.examination_date = examination_date
        ingestion.examination_time = examination_time
        first = db.scalar(select(ConfirmationItem).where(ConfirmationItem.ingestion_id == iid))
        for sequence, values in enumerate(entries, 1):
            row = first if sequence == 1 else ConfirmationItem(
                ingestion_id=iid, sequence_no=sequence, metric_name="合成指标", source_type="MANUAL",
                review_status="RESOLVED", resolution="MANUAL_ADDED")
            for key, value in values.items():
                setattr(row, key, value)
            db.add(row)
        db.commit()
    return commit(factory, user_id, iid)


def snapshot(factory):
    with factory() as db:
        return [{c.name: getattr(r, c.name) for c in LabResult.__table__.columns}
                for r in db.scalars(select(LabResult).order_by(LabResult.id))]


def legacy_reports(engine):
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as db:
        user = User(wechat_openid="stage06-synthetic")
        stranger = User(wechat_openid="stage06-stranger")
        db.add_all([user, stranger])
        db.flush()
        source = HealthProfile(user_id=user.id, display_name="合成源", relation="SELF")
        target = HealthProfile(user_id=user.id, display_name="合成目标", relation="OTHER")
        db.add_all([source, target])
        db.commit()
        uid, sid, source_id, target_id = user.id, stranger.id, source.id, target.id
        wbc = db.scalar(select(StandardMetric.id).where(StandardMetric.code == "WBC"))
        alt = db.scalar(select(StandardMetric.id).where(StandardMetric.code == "ALT"))
    base = {"standard_metric_id": wbc, "result_text": "5.1", "result_numeric": Decimal("5.1"),
            "comparator": None, "unit_original": " U ", "reference_text": "本次参考", "abnormal": None}
    entries = [
        base, {**base, "result_text": "5.2", "result_numeric": Decimal("5.2"), "unit_normalized": " U "},
        {**base, "comparator": "", "unit_original": "V"},
        {**base, "comparator": "=", "unit_original": None},
        *[{**base, "comparator": c, "result_text": c + "5.1"}
          for c in ("<", ">", "<=", ">=", "≤", "≥")],
        {**base, "result_text": "123", "result_numeric": None},
        {**base, "result_text": "阴性", "result_numeric": None},
        {**base, "standard_metric_id": None},  # Excluded; no name matching.
    ]
    older = formal(factory, uid, source_id, [base], date(2026, 7, 1))
    no_time = formal(factory, uid, source_id, entries, date(2026, 8, 1))
    morning = formal(factory, uid, source_id, [{**base, "unit_original": "V"}],
                     date(2026, 8, 1), time(8))
    evening = formal(factory, uid, source_id, [{**base, "result_text": "阴性", "result_numeric": None}],
                     date(2026, 8, 1), time(14))
    alt_report = formal(factory, uid, source_id, [{**base, "standard_metric_id": alt}], date(2026, 6, 1))
    return uid, sid, source_id, target_id, wbc, alt, older, no_time, morning, evening, alt_report


def migrate_confirmed(db, user, report_id, target):
    try:
        return reports.migrate_report(db, user, report_id, target)
    except ConfirmationError as exc:
        assert exc.code == "DUPLICATE_CONFIRM_REQUIRED"
        return reports.migrate_report(db, user, report_id, target, exc.details["acknowledgement"])


def exercise(engine, context):
    factory = sessionmaker(engine, expire_on_commit=False)
    uid, sid, source, target, mid, alt, older, no_time, morning, evening, alt_report = context
    with factory() as db:
        user = db.get(User, uid)
        detail = metrics.detail(db, user, source, mid)
        assert detail["history_count"] == 15 and detail["trend_plottable_count"] == 6
        assert detail["trend_series_count"] == 3
        assert detail["latest"]["report_id"] == evening
        assert detail["latest"]["result_text"] == "阴性"
        history = metrics.history(db, user, source, mid, page_size=100)["items"]
        assert [r["report_id"] for r in history[:2]] == [evening, morning]
        assert history[-1]["report_id"] == older
        assert len({r["lab_result_id"] for r in history}) == 15
        chart = metrics.trend(db, user, source, mid)
        assert [s["unit"] for s in chart["series"]] == ["V", "U", None]
        assert chart["plottable_count"] == 6
        points = [p for s in chart["series"] for p in s["points"]]
        assert len({p["lab_result_id"] for p in points}) == 6
        assert all(p["abnormal"] is None and p["reference_text"] == "本次参考" for p in points)
        v_points = chart["series"][0]["points"]
        assert [p["report_id"] for p in v_points] == [no_time, morning]
        assert v_points[0]["examination_time"] is None
        assert len(metrics.list_metrics(db, user, source)["items"]) == 2
    print("PostgreSQL latest NULLS LAST; trend NULLS FIRST; full same-day history; numeric admission and unit grouping: PASS")

    before = snapshot(factory)
    barrier = Barrier(2)
    def concurrent_put(_):
        with factory() as db:
            user = db.get(User, uid)
            barrier.wait(timeout=10)
            metrics.set_favorite(db, user, source, mid, True)
            db.commit()
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(concurrent_put, range(2)))
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(MetricFavorite)) == 1
        db.add(MetricFavorite(health_profile_id=source, standard_metric_id=mid))
        try:
            db.commit()
            raise AssertionError("favorite duplicate accepted")
        except IntegrityError:
            db.rollback()
        user = db.get(User, uid)
        db.get(StandardMetric, mid).status = "INACTIVE"
        db.commit()
        assert metrics.detail(db, user, source, mid)["is_favorite"]
    assert snapshot(factory) == before
    print("Favorite concurrent idempotence/UNIQUE and inactive StandardMetric historical visibility; formal snapshots unchanged: PASS")

    def session():
        with factory() as db:
            yield db
    app.dependency_overrides[auth.db_session] = session
    try:
        with TestClient(app) as api:
            owner_headers = {"Authorization": "Bearer " + auth.create_token(uid)}
            foreign_headers = {"Authorization": "Bearer " + auth.create_token(sid)}
            paths = [("GET", "/profile-metrics"), ("GET", f"/profile-metrics/{mid}"),
                     ("GET", f"/profile-metrics/{mid}/history"), ("GET", f"/profile-metrics/{mid}/trend"),
                     ("PUT", f"/favorites/{mid}"), ("DELETE", f"/favorites/{mid}")]
            for method, path in paths:
                denied = api.request(method, "/api/v1" + path, headers=foreign_headers,
                                     params={"health_profile_id": source})
                assert denied.status_code == 404 and denied.json()["code"] == "PROFILE_NOT_FOUND"
            for path in ("/profile-metrics", f"/profile-metrics/{mid}",
                         f"/profile-metrics/{mid}/history", f"/profile-metrics/{mid}/trend"):
                assert api.get("/api/v1" + path, headers=owner_headers,
                               params={"health_profile_id": source}).status_code == 200
    finally:
        app.dependency_overrides.clear()
    print("PostgreSQL-backed six API ownership checks and metric view serialization: PASS")

    # Existing Stage 05 operations; no summary/history synchronization.
    with factory() as db:
        user = db.get(User, uid)
        migrate_confirmed(db, user, evening, target)
        db.commit()
        assert metrics.detail(db, user, source, mid)["latest"]["report_id"] == morning
        assert metrics.detail(db, user, target, mid)["history_count"] == 1
        assert not metrics.detail(db, user, target, mid)["is_favorite"]
        migrate_confirmed(db, user, morning, target)
        db.commit()
        assert metrics.detail(db, user, source, mid)["latest"]["report_id"] == no_time
        assert metrics.trend(db, user, target, mid)["plottable_count"] == 1
        # Delete older result first, then the remaining latest report.
        for rid, expected in ((older, 12), (no_time, 0)):
            reports.delete_report(db, user, rid)
            db.commit()
            if expected:
                assert metrics.history(db, user, source, mid)["total"] == expected
                assert metrics.trend(db, user, source, mid)["plottable_count"] == 4
        assert [i["standard_metric"]["id"] for i in metrics.list_metrics(db, user, source)["items"]] == [alt]
        assert db.scalar(select(MetricFavorite.id).where(MetricFavorite.health_profile_id == source))
        assert reports.report_for(db, user, alt_report).id == alt_report
        # Return report to source after reactivating only test dictionary row.
        db.get(StandardMetric, mid).status = "ACTIVE"
        db.commit()
        migrate_confirmed(db, user, morning, source)
        db.commit()
        assert metrics.detail(db, user, source, mid)["is_favorite"]
        assert metrics.history(db, user, source, mid)["total"] == 1
    print("Stage 05 migrate/delete naturally change latest/history/trend; dormant favorite retained and restored; other report intact: PASS")


def schema_drift(engine, before_stage06=False):
    # Historical Stage 06 schema projection. Stage 07 verifies full current metadata
    # separately, including category/aliases; all original Stage 06 assertions remain.
    stage06_metadata = MetaData()
    for table in Base.metadata.sorted_tables:
        if table.name != "metric_aliases":
            copied = table.to_metadata(stage06_metadata)
            if table.name == "standard_metrics":
                copied._columns.remove(copied.c.category)
            if table.name == "file_cleanups":
                copied.indexes = {i for i in copied.indexes if i.name != "ix_file_cleanups_due"}
                copied._columns.remove(copied.c.not_before)
    with engine.connect() as conn:
        differences = compare_metadata(MigrationContext.configure(conn), stage06_metadata)
    if before_stage06:
        # Stage 06 ORM is already loaded while this database is still at 0005.
        # These are exactly the two not-yet-applied Stage 06 schema additions.
        added = [(action, item.name) for action, item in differences
                 if action == "add_table" or
                 (action == "add_index" and item.name == "ix_lab_results_profile_metric_date")]
        assert sorted(added) == [
            ("add_index", "ix_lab_results_profile_metric_date"), ("add_table", "metric_favorites")]
        differences = [(action, item) for action, item in differences
                       if action != "add_table" and
                       not (action == "add_index" and item.name == "ix_lab_results_profile_metric_date")]
    assert all(action in ("add_index", "remove_index") for action, _ in differences)
    signature = sorted((action, item.table.name, item.name, tuple(c.name for c in item.columns))
                       for action, item in differences)
    expected_legacy = [
        ("add_index", "ocr_tasks", "ix_ocr_tasks_status", ("status",)),
        ("remove_index", "ocr_tasks", "ix_ocr_tasks_queue", ("status", "next_attempt_at"))]
    assert signature == expected_legacy, signature
    return signature


def main():
    original_env = os.environ.get("DATABASE_URL")
    base_url = make_url(get_settings().database_url)
    admin = create_engine(base_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    names = ["checkup_stage06_" + kind + "_" + uuid4().hex[:12] for kind in ("upgrade", "clean")]
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
            if index == 0:
                command.upgrade(Config("alembic.ini"), "0005_report_management")
                context = legacy_reports(engine)
                before = snapshot(sessionmaker(engine))
                baseline_drift = schema_drift(engine, before_stage06=True)
                command.upgrade(Config("alembic.ini"), "0006_metric_trend")
                assert snapshot(sessionmaker(engine)) == before
                assert schema_drift(engine) == baseline_drift
                print("0005 existing formal snapshots unchanged across 0006; no OCR/re-commit/backfill: PASS")
            else:
                command.upgrade(Config("alembic.ini"), "0006_metric_trend")
                context = legacy_reports(engine)
            with engine.connect() as conn:
                assert conn.scalar(text("SELECT version_num FROM alembic_version")) == "0006_metric_trend"
            inspector = inspect(engine)
            assert any(c["column_names"] == ["health_profile_id", "standard_metric_id"]
                       for c in inspector.get_unique_constraints("metric_favorites"))
            assert any(i["column_names"] == ["health_profile_id", "standard_metric_id", "examination_date"]
                       for i in inspector.get_indexes("lab_results"))
            assert {c["name"] for c in inspector.get_columns("metric_favorites")} == {
                "id", "health_profile_id", "standard_metric_id", "created_at"}
            schema_drift(engine)
            print("Stage 06 schema matches ORM; only proven pre-existing Stage 03 OCR queue index drift remains: PASS")
            command.upgrade(Config("alembic.ini"), "head")
            exercise(engine, context)
            if index == 1:
                saved_before = snapshot(sessionmaker(engine))
                command.downgrade(Config("alembic.ini"), "0005_report_management")
                assert not inspect(engine).has_table("metric_favorites")
                assert snapshot(sessionmaker(engine)) == saved_before
                command.upgrade(Config("alembic.ini"), "0006_metric_trend")
                assert snapshot(sessionmaker(engine)) == saved_before
                schema_drift(engine)
                command.upgrade(Config("alembic.ini"), "head")
                print("0006 downgrade/re-upgrade preserves formal results: PASS")
            print(("0005 -> 0006" if index == 0 else "empty -> 0001..0006") + " migration/integration: PASS")
        print("PostgreSQL 17 Stage 06 integration: PASS")
    finally:
        for engine in engines:
            engine.dispose()
        with admin.connect() as conn:
            for name in created:
                assert name in names and name.startswith("checkup_stage06_")
                conn.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
            assert not conn.execute(text("SELECT datname FROM pg_database WHERE datname = ANY(:names)"),
                                    {"names": names}).all()
        admin.dispose()
        if original_env is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original_env
        get_settings.cache_clear()
        print(f"temporary databases removed and absence verified: {len(created)}")


if __name__ == "__main__":
    main()
