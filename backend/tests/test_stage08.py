"""Synthetic privacy lifecycle acceptance; real concurrency lives in the PG script."""
from datetime import UTC, timedelta

import pytest
from sqlalchemy import event, select
from test_stage02 import headers, ingestion, login, profile
from test_stage04 import add, new_report, old_ocr, patch, report_info, workspace
from test_stage05 import saved
from test_stage07 import admin
from test_stage07 import client as stage07_client

from app import cleanup_worker
from app.core import cos
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
)
from app.models.entities import now


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(cos, "delete_prefix", lambda prefix: None)
    yield from stage07_client.__wrapped__(monkeypatch)


def snapshot(factory):
    with factory() as db:
        return {table.name: sorted([dict(row) for row in db.execute(select(table)).mappings()],
                                   key=lambda row: str(row))
                for table in Base.metadata.sorted_tables}


def populated(api, factory, owner, pid):
    rid, _ = saved(api, owner, pid, report_no="manual")
    row, path = new_report(api, owner, pid)
    task_id = old_ocr(factory, row["id"])
    ws = workspace(api, owner, path)
    assert patch(api, owner, path, ws['items'][1]['id'], resolution='REMOVED').status_code == 200
    add(api, owner, path)
    report_info(api, owner, path, report_no="ocr", hospital_name="another synthetic")
    assert api.post(path + '/commit', headers=headers(owner), json={}).status_code == 200
    with factory() as db:
        db.get(OcrTask, task_id).run_no = 2
        db.flush()
        db.add(OcrTask(ingestion_id=row['id'], run_no=1, status='FAILED', input_manifest=[]))
        metric = db.scalar(select(StandardMetric))
        db.add(MetricFavorite(health_profile_id=pid, standard_metric_id=metric.id))
        if not db.scalar(select(MetricAlias)):
            db.add(MetricAlias(standard_metric_id=metric.id, alias='synthetic alias',
                              normalized_alias='syntheticalias', alias_type='SYNONYM'))
        db.commit()
    for status in ('UPLOADING', 'READY', 'QUEUED', 'OCR_FAILED', 'PENDING_CONFIRMATION'):
        draft = ingestion(api, owner, pid)
        with factory() as db:
            db.get(ReportIngestion, draft['id']).status = status
            if status == 'QUEUED':
                db.add(OcrTask(ingestion_id=draft['id'], run_no=1, status=status, input_manifest=[]))
            db.commit()
    return rid


def test_full_chain_impact_isolation_and_old_routes(client):
    api, factory = client
    owner = login(api, 'complete')
    pid = profile(api, owner)['id']
    rid = populated(api, factory, owner, pid)
    other = profile(api, owner, 'other')['id']
    populated(api, factory, owner, other)
    before = snapshot(factory)
    root = f'/api/v1/health-profiles/{pid}'
    impact = api.get(root + '/deletion-impact', headers=headers(owner)).json()
    assert impact == {'profile': {'id': pid, 'display_name': '本人'}, 'report_count': 2,
                      'unfinished_ingestion_count': 5, 'total_ingestion_count': 7,
                      'favorite_count': 1, 'processing_ocr_count': 0}
    with factory() as db:
        ids = list(db.scalars(select(ReportIngestion.id).where(ReportIngestion.health_profile_id == pid)))
        tids = list(db.scalars(select(OcrTask.id).where(OcrTask.ingestion_id.in_(ids))))
        aid = db.scalar(select(ReportAsset.id).where(ReportAsset.ingestion_id.in_(ids)))
    assert api.delete(root, headers=headers(owner)).status_code == 204
    with factory() as db:
        assert db.get(HealthProfile, pid) is None
        for model in (LabReport, LabResult, MetricFavorite, ReportIngestion):
            assert not db.scalars(select(model).where(model.health_profile_id == pid)).all()
        for model in (ConfirmationItem, OcrTask, ReportAsset, UploadAuthorization):
            assert not db.scalars(select(model).where(model.ingestion_id.in_(ids))).all()
        assert not db.scalars(select(OcrResultItem).where(OcrResultItem.ocr_task_id.in_(tids))).all()
        cleanups = db.scalars(select(FileCleanup)).all()
        assert {c.cos_object_key for c in cleanups} == {
            f"users/{owner['user']['id']}/ingestions/{iid}/" for iid in ids}
        assert all(c.target_type == 'PREFIX' for c in cleanups)
    after = snapshot(factory)
    for name in ('standard_metrics', 'metric_aliases'):
        assert before[name] == after[name]
    # Every surviving private record must be byte-for-byte unchanged.
    for name in ('lab_reports', 'lab_results', 'confirmation_items', 'ocr_result_items',
                 'ocr_tasks', 'report_assets', 'upload_authorizations', 'report_ingestions', 'metric_favorites'):
        assert after[name] and all(row in before[name] for row in after[name])
    paths = [root, root + '/deletion-impact', f'/api/v1/reports/{rid}',
             f'/api/v1/reports/{rid}/assets/{aid}/preview',
             f'/api/v1/reports?health_profile_id={pid}',
             f'/api/v1/profile-metrics?health_profile_id={pid}',
             f'/api/v1/ingestions?health_profile_id={pid}']
    paths += [f'/api/v1/ingestions/{iid}' for iid in ids]
    assert all(api.get(p, headers=headers(owner)).status_code == 404 for p in paths)
    assert api.delete(root, headers=headers(owner)).json()['code'] == 'PROFILE_NOT_FOUND'
    assert snapshot(factory) == after


@pytest.mark.parametrize('favorite', [False, True])
def test_default_nondefault_last_physical_delete(client, favorite):
    api, factory = client
    owner = login(api, 'defaults')
    pids = [profile(api, owner, str(i))['id'] for i in range(3)]
    with factory() as db:
        if favorite:
            db.add(MetricFavorite(health_profile_id=pids[0], standard_metric_id=db.scalar(select(StandardMetric.id))))
        # Equal times explicitly exercise the id tiebreaker.
        for pid in pids:
            db.get(HealthProfile, pid).created_at = now().replace(microsecond=0)
        db.commit()
    def remove(pid):
        assert api.delete(f'/api/v1/health-profiles/{pid}', headers=headers(owner)).status_code == 204
        with factory() as db:
            assert db.get(HealthProfile, pid) is None
        return api.get('/api/v1/me', headers=headers(owner)).json()['default_health_profile_id']
    replacement = min(pids[1:])
    assert remove(pids[0]) == replacement
    assert remove(next(p for p in pids[1:] if p != replacement)) == replacement
    assert remove(replacement) is None
    assert api.get('/api/v1/health-profiles', headers=headers(owner)).json() == []


def test_processing_is_task_status_and_atomic_then_retry(client):
    api, factory = client
    owner = login(api, 'busy'); pid = profile(api, owner)['id']
    populated(api, factory, owner, pid)
    with factory() as db:
        task = db.scalar(select(OcrTask).where(OcrTask.status == 'QUEUED'))
        task.status = 'PROCESSING'; tid = task.id
        db.commit()
    before = snapshot(factory)
    path = f'/api/v1/health-profiles/{pid}'
    assert api.get(path + '/deletion-impact', headers=headers(owner)).json()['processing_ocr_count'] == 1
    response = api.delete(path, headers=headers(owner))
    assert response.status_code == 409
    assert response.json()['code'] == 'PROFILE_DELETE_BUSY'
    assert response.json()['details'] == {'processing_count': 1}
    assert snapshot(factory) == before
    with factory() as db:
        db.get(OcrTask, tid).status = 'FAILED'; db.commit()
    assert api.delete(path, headers=headers(owner)).status_code == 204


@pytest.mark.parametrize('fragment', ['INSERT INTO file_cleanups', 'DELETE FROM lab_results',
    'DELETE FROM lab_reports', 'DELETE FROM ocr_result_items', 'DELETE FROM health_profiles'])
def test_atomic_failures_preserve_every_row(client, fragment):
    api, factory = client
    owner = login(api, 'rollback'); pid = profile(api, owner)['id']
    populated(api, factory, owner, pid)
    before = snapshot(factory)
    engine = factory.kw['bind']
    def abort(conn, cursor, statement, *args):
        if statement.startswith(fragment):
            raise RuntimeError('synthetic private payload must never be logged')
    event.listen(engine, 'before_cursor_execute', abort)
    try:
        response = api.delete(f'/api/v1/health-profiles/{pid}', headers=headers(owner))
        assert response.status_code == 500
        assert response.json()['code'] == 'PROFILE_DELETE_FAILED'
    finally:
        event.remove(engine, 'before_cursor_execute', abort)
    assert snapshot(factory) == before


def test_auth_isolation_and_no_sensitive_logs(client, caplog):
    api, factory = client
    owner, stranger = login(api, 'owner'), login(api, 'stranger')
    pid = profile(api, owner, 'PRIVATE_NAME')['id']
    before = snapshot(factory)
    root = f'/api/v1/health-profiles/{pid}'
    for path in (root, '/api/v1/health-profiles/unknown'):
        for method, suffix in ((api.get, '/deletion-impact'), (api.delete, '')):
            res = method(path + suffix, headers=headers(stranger))
            assert res.status_code == 404 and res.json()['code'] == 'PROFILE_NOT_FOUND'
            assert method(path + suffix).status_code == 401
    admin_headers = admin(api)
    assert api.delete(root, headers=admin_headers).status_code == 401
    assert api.get(root + '/deletion-impact', headers=admin_headers).status_code == 401
    assert snapshot(factory) == before
    assert api.delete(root, headers=headers(owner)).status_code == 204
    assert 'PRIVATE_NAME' not in caplog.text


def test_cleanup_windows_late_object_retry_and_privacy(client, monkeypatch, caplog):
    api, factory = client
    owner = login(api, 'window'); pid = profile(api, owner)['id']
    ids = [ingestion(api, owner, pid)['id'] for _ in range(3)]
    expiry = now() + timedelta(minutes=20)
    with factory() as db:
        for consumed, expiry_at, key in [(None, expiry - timedelta(minutes=2), 'unconsumed'),
                (now(), expiry, 'consumed'), (None, now() - timedelta(seconds=1), 'expired')]:
            db.add(UploadAuthorization(ingestion_id=ids[0], object_key=key,
                                      consumed_at=consumed, expires_at=expiry_at))
        db.add(UploadAuthorization(ingestion_id=ids[1], object_key='expired-only', expires_at=now()))
        db.commit()
    objects = set()
    def failure(prefix):
        raise RuntimeError('PRIVATE_NAME COS_SECRET temporary_token ' + prefix)
    monkeypatch.setattr(cos, 'delete_prefix', failure)
    assert api.delete(f'/api/v1/health-profiles/{pid}', headers=headers(owner)).status_code == 204
    with factory() as db:
        rows = list(db.scalars(select(FileCleanup)))
        delayed = next(c for c in rows if ids[0] in c.cos_object_key)
        assert delayed.not_before.replace(tzinfo=UTC) == expiry + timedelta(seconds=60)
        assert all(c.status == 'PENDING' for c in rows)
        assert all(c.not_before is None for c in rows if c.id != delayed.id)
        assert not cleanup_worker.process_cleanup(db, delayed)
        prefix, cid = delayed.cos_object_key, delayed.id
    assert cleanup_worker.run_once(factory) == 2
    objects.add(prefix + 'original/late.jpg')
    objects.add(prefix + 'ocr/retry/evidence.json')
    assert 'COS_SECRET' not in caplog.text and prefix not in caplog.text
    with factory() as db:
        db.get(FileCleanup, cid).not_before = now() - timedelta(seconds=1); db.commit()
    assert cleanup_worker.run_once(factory) == 3  # failure remains retryable
    def remove(prefix):
        objects.difference_update({key for key in objects if key.startswith(prefix)})
    monkeypatch.setattr(cos, 'delete_prefix', remove)
    assert cleanup_worker.run_once(factory) == 3
    assert not objects
    assert cleanup_worker.run_once(factory) == 0
    cleanup_worker.attempt_cleanup(factory, cid)
    with factory() as db:
        assert db.get(HealthProfile, pid) is None
        assert all(c.status == 'DONE' for c in db.scalars(select(FileCleanup)))
