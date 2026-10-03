"""Stage 08 PG17 migration, full-chain rollback and deterministic two-session races.

Only UUID disposable databases and synthetic COS objects are used.
"""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from time import monotonic, sleep
from uuid import uuid4

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from fastapi import HTTPException
from sqlalchemy import MetaData, create_engine, event, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker
from verify_postgres_reports import pending

from app import cleanup_worker, profile_metrics, reports
from app.api.v1 import business
from app.confirmation import ConfirmationError, commit_report
from app.core import cos
from app.core.config import get_settings
from app.db.base import Base
from app.models import (
    ConfirmationItem,
    FileCleanup,
    HealthProfile,
    LabReport,
    LabResult,
    MetricAlias,
    MetricFavorite,
    OcrResultItem,
    OcrTask,
    ReportAsset,
    ReportIngestion,
    StandardMetric,
    UploadAuthorization,
    User,
)
from app.models.entities import now
from app.ocr_queue import claim, fail
from app.profile_deletion import delete_profile, deletion_impact


def snapshot(factory):
    with factory() as db:
        return {table.name: sorted([dict(row) for row in db.execute(select(table)).mappings()],
                                   key=lambda row: str(row)) for table in Base.metadata.sorted_tables}


def owner(factory):
    with factory() as db:
        user = User(wechat_openid='synthetic-' + uuid4().hex)
        db.add(user); db.flush()
        profiles = [HealthProfile(user_id=user.id, display_name='synthetic', relation='OTHER') for _ in range(2)]
        db.add_all(profiles); db.flush()
        user.default_health_profile_id = profiles[0].id
        db.commit()
        return user.id, profiles[0].id, profiles[1].id


def full_chain(factory, uid, pid):
    """Two formal reports (OCR/manual), failed retry, removed item, all draft states."""
    metric_id = None
    ids = []
    for mode in ('OCR', 'MANUAL'):
        iid = pending(factory, uid, pid, report_no=uuid4().hex)
        ids.append(iid)
        with factory() as db:
            ingestion = business.ingestion_for(db, db.get(User, uid), iid, lock=True)
            ingestion.mode = mode
            metric_id = db.scalar(select(StandardMetric.id))
            item = db.scalar(select(ConfirmationItem).where(ConfirmationItem.ingestion_id == iid))
            item.standard_metric_id = metric_id
            if mode == 'OCR':
                asset = db.scalar(select(ReportAsset).where(ReportAsset.ingestion_id == iid))
                tasks = [OcrTask(ingestion_id=iid, run_no=n, status=status,
                                input_manifest=[{'asset_id': asset.id, 'page_no': 1}],
                                result_summary={'total_count': 1})
                         for n, status in ((1, 'FAILED'), (2, 'SUCCEEDED'))]
                db.add_all(tasks); db.flush()
                for t in tasks:
                    row = OcrResultItem(ocr_task_id=t.id, sequence_no=1, source_asset_id=asset.id,
                        page_no=1, raw_metric='synthetic', raw_result='synthetic private',
                        final_decision='FINAL_AUTO', review_reasons=[], evidence={}, payload={})
                    db.add(row); db.flush()
                    if t.run_no == 2:
                        item.source_ocr_result_item_id = row.id
                        item.source_type = 'OCR_AUTO'; item.resolution = 'ACCEPTED'
            db.add(ConfirmationItem(ingestion_id=iid, sequence_no=2, metric_name='removed',
                result_text='synthetic', source_type='MANUAL', review_status='RESOLVED', resolution='REMOVED'))
            try:
                commit_report(db, ingestion)
            except ConfirmationError as exc:
                assert exc.code == 'DUPLICATE_CONFIRM_REQUIRED'
                commit_report(db, ingestion, exc.details['acknowledgement'])
            db.commit()
    with factory() as db:
        db.add(MetricFavorite(health_profile_id=pid, standard_metric_id=metric_id))
        if not db.scalar(select(MetricAlias.id)):
            db.add(MetricAlias(standard_metric_id=metric_id, alias='SyntheticAlias',
                              normalized_alias='syntheticalias', alias_type='SYNONYM'))
        for status in ('UPLOADING', 'READY', 'QUEUED', 'OCR_FAILED', 'PENDING_CONFIRMATION'):
            row = ReportIngestion(user_id=uid, health_profile_id=pid, status=status)
            db.add(row); db.flush(); ids.append(row.id)
            if status == 'QUEUED':
                db.add(OcrTask(ingestion_id=row.id, run_no=1, status='QUEUED', input_manifest=[]))
        expiry = now() + timedelta(minutes=20)
        for n, consumed, expiration in ((1, None, expiry - timedelta(minutes=1)),
                                        (2, now(), expiry), (3, now(), now() - timedelta(seconds=1))):
            db.add(UploadAuthorization(object_key=f'synthetic/{ids[-1]}/{n}', ingestion_id=ids[-1],
                                      expires_at=expiration, consumed_at=consumed))
        db.commit()
    return ids, expiry


def no_orphans(engine):
    with engine.connect() as conn:
        for table in Base.metadata.sorted_tables:
            for fk in table.foreign_keys:
                target = fk.column
                sql = (f'SELECT count(*) FROM "{table.name}" c LEFT JOIN "{target.table.name}" p '
                       f'ON c."{fk.parent.name}" = p."{target.name}" '
                       f'WHERE c."{fk.parent.name}" IS NOT NULL AND p."{target.name}" IS NULL')
                assert conn.scalar(text(sql)) == 0, (table.name, fk.parent.name)
        assert conn.scalar(text('SELECT count(*) FROM users u LEFT JOIN health_profiles p '
            'ON p.id=u.default_health_profile_id WHERE u.default_health_profile_id IS NOT NULL AND p.id IS NULL')) == 0


def full_and_rollback(engine, factory):
    uid, pid, other = owner(factory)
    ids, expiry = full_chain(factory, uid, pid)
    full_chain(factory, uid, other)
    before = snapshot(factory)
    for fragment in ('INSERT INTO file_cleanups', 'DELETE FROM lab_results', 'DELETE FROM lab_reports',
                     'DELETE FROM ocr_result_items', 'DELETE FROM health_profiles'):
        def abort(conn, cursor, statement, *args, fragment=fragment):
            if statement.startswith(fragment):
                conn.exec_driver_sql('SELECT 1 / 0')
        event.listen(engine, 'before_cursor_execute', abort)
        try:
            with factory() as db:
                try:
                    delete_profile(db, uid, pid); db.commit()
                    raise AssertionError('rollback injection did not execute')
                except DBAPIError:
                    db.rollback()
        finally:
            event.remove(engine, 'before_cursor_execute', abort)
        assert snapshot(factory) == before
    print('PG rollback: cleanup / LabResult / LabReport / OCR / HealthProfile; complete snapshots unchanged: PASS')
    with factory() as db:
        impact = deletion_impact(db, uid, pid)
        assert [impact[k] for k in ('report_count', 'unfinished_ingestion_count', 'total_ingestion_count', 'favorite_count')] == [2, 5, 7, 1]
        cleanup_ids = delete_profile(db, uid, pid); db.commit()
        assert db.get(HealthProfile, pid) is None
        for model in (MetricFavorite, LabResult, LabReport, ReportIngestion):
            assert not db.scalars(select(model).where(model.health_profile_id == pid)).all()
        for model in (ConfirmationItem, OcrTask, UploadAuthorization, ReportAsset):
            assert not db.scalars(select(model).where(model.ingestion_id.in_(ids))).all()
        rows = list(db.scalars(select(FileCleanup).where(FileCleanup.id.in_(cleanup_ids))))
        assert len(rows) == len(ids) == 7
        assert all(row.status == 'PENDING' and row.target_type == 'PREFIX' for row in rows)
        delayed = next(row for row in rows if ids[-1] in row.cos_object_key)
        assert delayed.not_before == expiry + timedelta(seconds=60)
        assert all(row.not_before is None for row in rows if row.id != delayed.id)
        assert db.get(User, uid).default_health_profile_id == other
    after = snapshot(factory)
    for name in ('standard_metrics', 'metric_aliases'):
        assert before[name] == after[name]
    for name in ('lab_results', 'lab_reports', 'ocr_tasks', 'ocr_result_items', 'confirmation_items',
                 'report_assets', 'report_ingestions', 'upload_authorizations', 'metric_favorites'):
        assert after[name] and all(row in before[name] for row in after[name])
    print('PG full-chain deletion, seven PREFIX records, surviving private/public snapshots unchanged: PASS')
    original = cos.delete_prefix
    objects = {delayed.cos_object_key + 'original/late.jpg', delayed.cos_object_key + 'ocr/retry/evidence'}
    calls = []
    def remove(prefix):
        calls.append(prefix)
        objects.difference_update({key for key in objects if key.startswith(prefix)})
    try:
        cos.delete_prefix = remove
        cleanup_worker.run_once(factory)
        assert objects and delayed.cos_object_key not in calls
        with factory() as db:
            db.get(FileCleanup, delayed.id).not_before = now() - timedelta(seconds=1); db.commit()
        cos.delete_prefix = lambda prefix: (_ for _ in ()).throw(RuntimeError('synthetic COS outage'))
        cleanup_worker.run_once(factory)
        with factory() as db:
            assert db.get(FileCleanup, delayed.id).status == 'PENDING'
            assert db.get(HealthProfile, pid) is None
        cos.delete_prefix = remove
        cleanup_worker.run_once(factory); cleanup_worker.run_once(factory)
        assert not objects and calls.count(delayed.cos_object_key) == 1
    finally:
        cos.delete_prefix = original
    no_orphans(engine)
    # Remove the other fixture's queued tasks so claim tests have a single candidate.
    with factory() as db:
        delete_profile(db, uid, other); db.commit()
    print('PG not_before / consumed STS / late object / COS failure / retry / idempotence: PASS')


def serialized(engine, factory, first, second):
    """Prove the second real backend waits on the first, not just two serial calls."""
    held, release, started = Event(), Event(), Event()
    pids = {}
    def run_first():
        with factory() as db:
            pids['first'] = db.scalar(text('SELECT pg_backend_pid()'))
            def hold_commit(session):
                session.flush()
                held.set()
                assert release.wait(15)
            event.listen(db, 'before_commit', hold_commit, once=True)
            value = first(db)
            db.commit()
            return value
    def run_second():
        assert held.wait(15)
        with factory() as db:
            pids['second'] = db.scalar(text('SELECT pg_backend_pid()'))
            started.set()
            try:
                value = second(db); db.commit(); return value
            except (HTTPException, ConfirmationError) as exc:
                db.rollback()
                return exc.detail if isinstance(exc, HTTPException) else exc.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(run_first); b = pool.submit(run_second)
        try:
            assert started.wait(15)
            until = monotonic() + 8
            with engine.connect() as conn:
                while monotonic() < until:
                    blockers = conn.scalar(text('SELECT pg_blocking_pids(:pid)'), {'pid': pids['second']})
                    if pids['first'] in blockers:
                        break
                    sleep(0.02)
                else:
                    raise AssertionError('real PostgreSQL lock wait not observed')
        finally:
            release.set()
        return a.result(timeout=20), b.result(timeout=20)


def races(engine, factory):
    for kind in ('commit', 'migrate_source', 'migrate_target', 'upload', 'favorite', 'new_ingestion', 'default'):
        for deletion_first in (False, True):
            rid = None
            uid, source, target = owner(factory)
            iid = pending(factory, uid, source, report_no=uuid4().hex)
            with factory() as db:
                metric = db.scalar(select(StandardMetric.id))
                if kind.startswith('migrate'):
                    rid = commit_report(db, business.ingestion_for(db, db.get(User, uid), iid, lock=True)).id
                if kind == 'upload':
                    db.get(ReportIngestion, iid).status = 'READY'
                db.commit()
            deleting = target if kind == 'migrate_target' else source
            issued = now() + timedelta(minutes=30)
            original = business.upload_credential
            business.upload_credential = lambda key, issued=issued: {'object_key': key, 'expired_time': issued.timestamp()}
            def operation(db, uid=uid, kind=kind, iid=iid, rid=rid, target=target,
                          source=source, metric=metric):
                user = db.get(User, uid)
                if kind == 'commit':
                    return commit_report(db, business.ingestion_for(db, user, iid, lock=True)).id
                if kind.startswith('migrate'):
                    return reports.migrate_report(db, user, rid, target).id
                if kind == 'upload':
                    return business.authorize_upload(iid, business.UploadRequest(mime_type='image/jpeg'), user, db)
                if kind == 'favorite':
                    return profile_metrics.set_favorite(db, user, source, metric, True)
                if kind == 'default':
                    return business.set_default(business.DefaultProfile(health_profile_id=source), user, db)
                return business.create_ingestion(business.IngestionInput(health_profile_id=source), user, db)
            def deletion(db, uid=uid, deleting=deleting):
                return delete_profile(db, uid, deleting)
            try:
                _first, b = serialized(engine, factory, deletion if deletion_first else operation,
                                  operation if deletion_first else deletion)
                if deletion_first:
                    assert b in ('PROFILE_NOT_FOUND', 'REPORT_NOT_FOUND'), (kind, b)
                with factory() as db:
                    assert db.get(HealthProfile, deleting) is None
                    if kind.startswith('migrate') and not deletion_first and deleting == source:
                        assert db.get(LabReport, rid).health_profile_id == target
                        assert db.get(ReportIngestion, iid).health_profile_id == target
                        assert all(r.health_profile_id == target for r in reports.results_for(db, rid))
                    elif kind != 'migrate_target' or not deletion_first:
                        assert db.get(ReportIngestion, iid) is None
                    if kind == 'upload' and not deletion_first:
                        cleanup = db.scalar(select(FileCleanup).where(FileCleanup.cos_object_key == f'users/{uid}/ingestions/{iid}/'))
                        assert cleanup.not_before == issued + timedelta(seconds=60)
                no_orphans(engine)
            finally:
                business.upload_credential = original
            print(f'PG race {kind}, deletion_first={deletion_first}, observed blocking and no orphans: PASS')


def queued_races(engine, factory):
    uid, pid, _ = owner(factory)
    with factory() as db:
        ingestion = ReportIngestion(user_id=uid, health_profile_id=pid, status='QUEUED')
        db.add(ingestion); db.flush()
        task = OcrTask(ingestion_id=ingestion.id, run_no=1, status='QUEUED', input_manifest=[])
        db.add(task); db.commit(); tid, iid = task.id, ingestion.id
    with factory() as deleting:
        delete_profile(deleting, uid, pid)  # holds the task deletion lock, not committed
        with factory() as worker:
            assert claim(worker, 'synthetic-worker') is None
        deleting.commit()
    with factory() as db:
        assert db.get(OcrTask, tid) is None and db.get(ReportIngestion, iid) is None
        assert not fail(db, tid, 'synthetic-worker', 'SYNTHETIC')
    uid, pid, _ = owner(factory)
    with factory() as db:
        row = ReportIngestion(user_id=uid, health_profile_id=pid, status='QUEUED')
        db.add(row); db.flush()
        task = OcrTask(ingestion_id=row.id, run_no=1, status='QUEUED', input_manifest=[])
        db.add(task); db.commit(); tid = task.id
    # Hold the actual claim just before its commit. Deletion must wait on task lock,
    # then refresh PROCESSING rather than use a stale QUEUED identity-map object.
    held, release = Event(), Event()
    def worker_claim():
        with factory() as db:
            def before_commit(session):
                held.set(); assert release.wait(15)
            event.listen(db, 'before_commit', before_commit, once=True)
            return claim(db, 'synthetic-worker').id
    def deleting():
        assert held.wait(15)
        with factory() as db:
            try:
                delete_profile(db, uid, pid)
                raise AssertionError('PROCESSING deletion allowed')
            except ConfirmationError as exc:
                assert exc.code == 'PROFILE_DELETE_BUSY' and exc.details == {'processing_count': 1}
                db.rollback()
    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(worker_claim); assert held.wait(15)
        b = pool.submit(deleting)
        try:
            sleep(0.15); assert not b.done()
        finally:
            release.set()
        assert a.result(timeout=20) == tid; b.result(timeout=20)
    with factory() as db:
        assert db.get(HealthProfile, pid) is not None
        assert db.get(OcrTask, tid).status == 'PROCESSING'
        assert not db.scalar(select(FileCleanup.id).where(FileCleanup.cos_object_key.like(f'%{row.id}%')))
        assert fail(db, tid, 'synthetic-worker', 'SYNTHETIC')
        delete_profile(db, uid, pid); db.commit()
    no_orphans(engine)
    print('PG real QUEUED claim: deletion wins SKIP LOCKED / claim wins BUSY rollback / terminal retry: PASS')


def schema(engine):
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert sorted((action, item.name) for action, item in diff) == [
        ('add_index', 'ix_ocr_tasks_status'), ('remove_index', 'ix_ocr_tasks_queue')], diff
    columns = {c['name']: c for c in inspect(engine).get_columns('file_cleanups')}
    assert columns['not_before']['nullable'] and columns['not_before']['type'].timezone
    assert any(i['name'] == 'ix_file_cleanups_due' for i in inspect(engine).get_indexes('file_cleanups'))


def main():
    original_env = os.environ.get('DATABASE_URL')
    base = make_url(get_settings().database_url)
    admin = create_engine(base.set(database='postgres'), isolation_level='AUTOCOMMIT')
    names = ['checkup_stage08_' + kind + '_' + uuid4().hex[:12] for kind in ('upgrade', 'clean')]
    engines, created = [], []
    try:
        with admin.connect() as conn:
            assert int(conn.scalar(text('SHOW server_version_num'))) // 10000 == 17
        for index, name in enumerate(names):
            with admin.connect() as conn:
                conn.execute(text(f'CREATE DATABASE "{name}"'))
            created.append(name)
            url = base.set(database=name)
            os.environ['DATABASE_URL'] = url.render_as_string(hide_password=False); get_settings.cache_clear()
            engine = create_engine(url); engines.append(engine)
            if index == 0:
                command.upgrade(Config('alembic.ini'), '0007_standard_metric_admin')
                metadata = MetaData(); metadata.reflect(engine)
                table = metadata.tables['file_cleanups']
                with engine.begin() as conn:
                    for target in ('OBJECT', 'PREFIX'):
                        for status in ('PENDING', 'DONE'):
                            conn.execute(table.insert().values(id=str(uuid4()), target_type=target,
                                status=status, cos_object_key=f'legacy/{target}/{status}', created_at=now()))
                with engine.connect() as conn:
                    before = list(conn.execute(select(table).order_by(table.c.id)).mappings())
            command.upgrade(Config('alembic.ini'), 'head')
            schema(engine)
            with engine.connect() as conn:
                assert conn.scalar(text('SELECT version_num FROM alembic_version')) == '0008_profile_data_deletion'
                if index == 0:
                    assert list(conn.execute(select(table).order_by(table.c.id)).mappings()) == before
                    assert conn.scalar(text('SELECT count(*) FROM file_cleanups WHERE not_before IS NOT NULL')) == 0
            factory = sessionmaker(engine, expire_on_commit=False)
            # Legacy synthetic invalid prefixes aren't executable cleanup targets.
            with engine.begin() as conn:
                conn.execute(text('DELETE FROM file_cleanups'))
            print(('PG 0007 -> 0008 legacy OBJECT/PREFIX/PENDING/DONE preserved' if index == 0 else 'PG empty 0001 -> 0008') + ': PASS')
            full_and_rollback(engine, factory)
            races(engine, factory)
            queued_races(engine, factory)
            schema(engine); no_orphans(engine)
        print('PostgreSQL 17 Stage 08: PASS')
    finally:
        for engine in engines:
            engine.dispose()
        with admin.connect() as conn:
            for name in created:
                assert name in names and name.startswith('checkup_stage08_')
                conn.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
            assert not conn.execute(text('SELECT datname FROM pg_database WHERE datname = ANY(:names)'), {'names': names}).all()
        admin.dispose()
        if original_env is None:
            os.environ.pop('DATABASE_URL', None)
        else:
            os.environ['DATABASE_URL'] = original_env
        get_settings.cache_clear()
        print(f'Stage 08 temporary databases removed and absence verified: {len(created)}')


if __name__ == '__main__':
    main()
