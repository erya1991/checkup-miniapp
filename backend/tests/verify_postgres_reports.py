"""Stage 05 acceptance in isolated PostgreSQL 17 databases, never the business DB."""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier, Event
from uuid import uuid4

from alembic import command
from alembic.config import Config
from fastapi import HTTPException
from sqlalchemy import MetaData, create_engine, event, func, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker
from verify_postgres_confirmation import exercise as exercise_stage04
from verify_postgres_confirmation import legacy_fixture

from app import cleanup_worker, reports
from app.api.v1.business import ingestion_for
from app.confirmation import ConfirmationError, commit_report
from app.core import cos
from app.core.config import get_settings
from app.models import (
    ConfirmationItem,
    FileCleanup,
    HealthProfile,
    LabReport,
    LabResult,
    OcrResultItem,
    OcrTask,
    ReportAsset,
    ReportIngestion,
    UploadAuthorization,
    User,
)
from app.models.entities import now


def pending(factory, user_id, profile_id, report_no=None):
    with factory() as db:
        ingestion = ReportIngestion(user_id=user_id, health_profile_id=profile_id,
            mode='MANUAL', status='PENDING_CONFIRMATION', examination_date=date(2026, 8, 2),
            hospital_name='合成医院', report_no=report_no, confirmation_initialized_at=now())
        db.add(ingestion)
        db.flush()
        asset = ReportAsset(ingestion_id=ingestion.id, cos_object_key=f'synthetic/{ingestion.id}',
                            page_no=1, mime_type='image/jpeg', file_size=123)
        db.add(asset)
        db.add(UploadAuthorization(object_key=asset.cos_object_key, ingestion_id=ingestion.id, expires_at=now()))
        db.add(ConfirmationItem(ingestion_id=ingestion.id, sequence_no=1, metric_name='合成指标',
                               result_text='阴性', source_type='MANUAL', review_status='RESOLVED',
                               resolution='MANUAL_ADDED'))
        db.commit()
        return ingestion.id


def commit(factory, user_id, ingestion_id):
    with factory() as db:
        ingestion = ingestion_for(db, db.get(User, user_id), ingestion_id, lock=True)
        try:
            row = commit_report(db, ingestion)
        except ConfirmationError as exc:
            assert exc.code == 'DUPLICATE_CONFIRM_REQUIRED'
            row = commit_report(db, ingestion, exc.details['acknowledgement'])
        db.commit()
        return row.id


def consistent(factory, rid, iid):
    with factory() as db:
        report = db.get(LabReport, rid)
        if report is None:
            assert db.get(ReportIngestion, iid) is None
            assert db.scalar(select(func.count()).select_from(LabResult).where(LabResult.report_id == rid)) == 0
        else:
            assert report.health_profile_id == db.get(ReportIngestion, iid).health_profile_id
            assert all(r.health_profile_id == report.health_profile_id for r in reports.results_for(db, rid))


def exercise(engine, user_id, old_iid):
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as db:
        user = db.get(User, user_id)
        source = db.get(ReportIngestion, old_iid).health_profile_id
        targets = [HealthProfile(user_id=user_id, display_name=f'合成档案{i}', relation='OTHER') for i in range(3)]
        db.add_all(targets)
        db.commit()
        p1, p2, p3 = [p.id for p in targets]
        legacy = db.scalar(select(LabReport).where(LabReport.source_ingestion_id == old_iid))
        assert reports.detail(db, user, legacy)['item_count'] == 2
        assert db.scalar(select(FileCleanup).where(FileCleanup.cos_object_key == 'legacy/object')).target_type == 'OBJECT'
    print('Stage 04 existing report readable without re-commit; legacy OBJECT backfill: PASS')

    iid = pending(factory, user_id, source)
    rid = commit(factory, user_id, iid)
    # Inject a real PostgreSQL failure after the ingestion update, before formal row update.
    def abort_update(conn, cursor, statement, *args):
        if statement.startswith('UPDATE lab_reports'):
            conn.exec_driver_sql('SELECT 1 / 0')
    event.listen(engine, 'before_cursor_execute', abort_update)
    try:
        with factory() as db:
            try:
                reports.migrate_report(db, db.get(User, user_id), rid, p1)
                db.commit()
                raise AssertionError('migration rollback not exercised')
            except DBAPIError:
                db.rollback()
    finally:
        event.remove(engine, 'before_cursor_execute', abort_update)
    consistent(factory, rid, iid)
    with factory() as db:
        assert db.get(LabReport, rid).health_profile_id == source
    print('PostgreSQL migrate partial-update rollback: PASS')

    barrier = Barrier(2)
    def migrate(target):
        with factory() as db:
            barrier.wait(timeout=15)
            reports.migrate_report(db, db.get(User, user_id), rid, target)
            db.commit()
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(migrate, t) for t in (p1, p2)]
        for f in futures:
            f.result(timeout=30)
    consistent(factory, rid, iid)
    print('two sessions migrate vs migrate, three profile columns consistent: PASS')

    # A commit holds the same target-profile row lock; migration must see its duplicate after waiting.
    target_iid = pending(factory, user_id, p3)
    ready, release = Event(), Event()
    def holding_commit():
        with factory() as db:
            ingestion = ingestion_for(db, db.get(User, user_id), target_iid, lock=True)
            db.scalar(select(HealthProfile).where(HealthProfile.id == p3).with_for_update())
            ready.set()
            assert release.wait(15)
            row = commit_report(db, ingestion)
            db.commit()
            return row.id
    def waiting_migrate():
        assert ready.wait(15)
        with factory() as db:
            try:
                reports.migrate_report(db, db.get(User, user_id), rid, p3)
                raise AssertionError('concurrent target commit was not detected')
            except ConfirmationError as exc:
                db.rollback()
                assert exc.code == 'DUPLICATE_CONFIRM_REQUIRED'
                return exc.details
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(holding_commit)
        second = pool.submit(waiting_migrate)
        assert ready.wait(15)
        release.set()
        candidate = first.result(timeout=30)
        details = second.result(timeout=30)
    assert [c['report_id'] for c in details['candidates']] == [candidate]
    consistent(factory, rid, iid)
    print('migration vs target new commit, duplicate serialized: PASS')

    # Cleanup insertion error, then late deletion error, both roll back the full chain.
    for fragment in ('INSERT INTO file_cleanups', 'DELETE FROM report_assets'):
        def abort_delete(conn, cursor, statement, *args, fragment=fragment):
            if statement.startswith(fragment):
                conn.exec_driver_sql('SELECT 1 / 0')
        event.listen(engine, 'before_cursor_execute', abort_delete)
        try:
            with factory() as db:
                try:
                    reports.delete_report(db, db.get(User, user_id), rid)
                    db.commit()
                    raise AssertionError('delete rollback not exercised')
                except DBAPIError:
                    db.rollback()
        finally:
            event.remove(engine, 'before_cursor_execute', abort_delete)
        consistent(factory, rid, iid)
        with factory() as db:
            assert db.get(LabReport, rid)
            assert not db.scalar(select(FileCleanup).where(FileCleanup.target_type == 'PREFIX'))
    print('cleanup insertion and late delete PostgreSQL rollback: PASS')

    barrier = Barrier(2)
    def moving():
        with factory() as db:
            barrier.wait(timeout=15)
            try:
                reports.migrate_report(db, db.get(User, user_id), rid, source)
                db.commit()
            except HTTPException as exc:
                db.rollback()
                assert exc.status_code == 404
    def deleting():
        with factory() as db:
            barrier.wait(timeout=15)
            cleanup_id = reports.delete_report(db, db.get(User, user_id), rid)
            db.commit()
            return cleanup_id
    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = pool.submit(moving), pool.submit(deleting)
        first.result(timeout=30)
        cleanup_id = second.result(timeout=30)
    consistent(factory, rid, iid)
    with factory() as db:
        for model in (ConfirmationItem, OcrTask, ReportAsset, UploadAuthorization):
            assert db.scalar(select(func.count()).select_from(model).where(model.ingestion_id == iid)) == 0
        assert db.get(FileCleanup, cleanup_id).status == 'PENDING'
        try:
            reports.delete_report(db, db.get(User, user_id), rid)
            raise AssertionError('repeated delete accepted')
        except HTTPException as exc:
            assert exc.status_code == 404
        db.rollback()
    print('migrate vs delete and repeated DELETE: PASS')

    # Concurrent repeated DELETE must produce one durable prefix record.
    repeated_iid = pending(factory, user_id, source, report_no='DELETE-CONCURRENT')
    repeated_rid = commit(factory, user_id, repeated_iid)
    barrier = Barrier(2)
    def repeated_delete():
        with factory() as db:
            barrier.wait(timeout=15)
            try:
                reports.delete_report(db, db.get(User, user_id), repeated_rid)
                db.commit()
                return 204
            except HTTPException as exc:
                db.rollback()
                assert exc.status_code == 404
                return 404
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(repeated_delete) for _ in range(2)]
        assert sorted(f.result(timeout=30) for f in futures) == [204, 404]
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(FileCleanup).where(
            FileCleanup.cos_object_key == f'users/{user_id}/ingestions/{repeated_iid}/')) == 1
    consistent(factory, repeated_rid, repeated_iid)
    print('two sessions repeated DELETE produces exactly one PREFIX: PASS')

    # Delete legacy OCR report: includes both source rows and resolved/removed confirmation rows.
    with factory() as db:
        legacy = db.scalar(select(LabReport).where(LabReport.source_ingestion_id == old_iid))
        legacy_id = legacy.id
        task_ids = list(db.scalars(select(OcrTask.id).where(OcrTask.ingestion_id == old_iid)))
        cid = reports.delete_report(db, db.get(User, user_id), legacy_id)
        db.commit()
    with factory() as db:
        assert not db.get(LabReport, legacy_id) and not db.get(ReportIngestion, old_iid)
        assert db.scalar(select(func.count()).select_from(LabResult).where(LabResult.report_id == legacy_id)) == 0
        assert db.scalar(select(func.count()).select_from(OcrResultItem).where(OcrResultItem.ocr_task_id.in_(task_ids))) == 0
        for model in (ConfirmationItem, OcrTask, ReportAsset, UploadAuthorization):
            assert db.scalar(select(func.count()).select_from(model).where(model.ingestion_id == old_iid)) == 0
        assert db.get(FileCleanup, cid).target_type == 'PREFIX'
    print('full OCR/confirmation/formal/source chain hard deletion: PASS')

    # No real COS mutation: exercise durable consumer with an isolated synthetic storage stub.
    original_prefix, original_object = cos.delete_prefix, cos.delete_object
    calls = []
    try:
        cos.delete_prefix = lambda key: (_ for _ in ()).throw(RuntimeError('synthetic unavailable'))
        cos.delete_object = calls.append
        cleanup_worker.run_once(factory)
        with factory() as db:
            assert db.get(FileCleanup, cid).status == 'PENDING'
        cos.delete_prefix = calls.append
        cleanup_worker.run_once(factory)
        cleanup_worker.run_once(factory)
        with factory() as db:
            assert db.get(FileCleanup, cid).status == 'DONE'
            assert db.get(FileCleanup, cleanup_id).status == 'DONE'
        assert len(calls) == 4
    finally:
        cos.delete_prefix, cos.delete_object = original_prefix, original_object
    print('durable PREFIX/OBJECT consumer, COS failure retry and repeat safe: PASS')


def main():
    original_env = os.environ.get('DATABASE_URL')
    base_url = make_url(get_settings().database_url)
    admin = create_engine(base_url.set(database='postgres'), isolation_level='AUTOCOMMIT')
    names = ['checkup_stage05_' + suffix + '_' + uuid4().hex[:12] for suffix in ('upgrade', 'clean')]
    created, engines = [], []
    try:
        with admin.connect() as conn:
            assert int(conn.scalar(text('SHOW server_version_num'))) // 10000 == 17
        for index, name in enumerate(names):
            with admin.connect() as conn:
                conn.execute(text(f'CREATE DATABASE "{name}"'))
            created.append(name)
            url = base_url.set(database=name)
            os.environ['DATABASE_URL'] = url.render_as_string(hide_password=False)
            get_settings.cache_clear()
            engine = create_engine(url)
            engines.append(engine)
            if index == 0:
                command.upgrade(Config('alembic.ini'), '0003_ocr')
                uid, iid, tid = legacy_fixture(engine)
                command.upgrade(Config('alembic.ini'), '0004_confirmation_report')
                exercise_stage04(engine, uid, iid, tid)
                tables = MetaData()
                tables.reflect(engine)
                with engine.begin() as conn:
                    conn.execute(tables.tables['file_cleanups'].insert(),
                                 {'id': str(uuid4()), 'cos_object_key': 'legacy/object', 'status': 'PENDING', 'created_at': now()})
                command.upgrade(Config('alembic.ini'), 'head')
                exercise(engine, uid, iid)
            else:
                command.upgrade(Config('alembic.ini'), 'head')
            with engine.connect() as conn:
                assert conn.scalar(text('SELECT version_num FROM alembic_version')) == '0005_report_management'
            assert any(c['name'] == 'ck_file_cleanup_target_type' for c in inspect(engine).get_check_constraints('file_cleanups'))
            print(('0004 -> 0005' if index == 0 else 'empty -> 0001..0005') + ' migration: PASS')
        print('PostgreSQL 17 Stage 05 integration: PASS')
    finally:
        for engine in engines:
            engine.dispose()
        with admin.connect() as conn:
            for name in created:
                assert name in names and name.startswith('checkup_stage05_')
                conn.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
            remaining = conn.execute(text("SELECT datname FROM pg_database WHERE datname = ANY(:names)"), {'names': names}).all()
            assert not remaining
        admin.dispose()
        if original_env is None:
            os.environ.pop('DATABASE_URL', None)
        else:
            os.environ['DATABASE_URL'] = original_env
        get_settings.cache_clear()
        print(f'temporary databases removed and absence verified: {len(created)}')


if __name__ == '__main__':
    main()
