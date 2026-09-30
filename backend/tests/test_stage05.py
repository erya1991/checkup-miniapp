"""Stage 05 synthetic API and cleanup safety acceptance."""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import event, func, select
from test_stage02 import asset, headers, ingestion, login, profile
from test_stage04 import add, new_report, old_ocr, report_info, workspace
from test_stage04 import client as stage04_client

from app import cleanup_worker
from app.api.v1 import business
from app.api.v1 import reports as report_api
from app.core import cos
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
)


@pytest.fixture
def client(monkeypatch):
    yield from stage04_client.__wrapped__(monkeypatch)


def saved(api, owner, profile_id, **info):
    row, path = new_report(api, owner, profile_id, manual=True)
    report_info(api, owner, path, **info)
    add(api, owner, path)
    response = api.post(path + "/commit", headers=headers(owner), json={})
    if response.status_code == 409:
        response = api.post(path + "/commit", headers=headers(owner),
                            json={"duplicate_acknowledgement": response.json()["details"]["acknowledgement"]})
    assert response.status_code == 200, response.text
    return response.json()["report_id"], row["id"]


def test_list_formal_only_profile_pagination_sort_and_counts(client):
    api, factory = client
    owner = login(api, "list")
    p = profile(api, owner)["id"]
    other = profile(api, owner, "父亲", "FATHER")["id"]
    for status in ("UPLOADING", "READY", "QUEUED", "PROCESSING", "OCR_FAILED", "PENDING_CONFIRMATION"):
        draft = ingestion(api, owner, p)
        with factory() as db:
            db.get(ReportIngestion, draft["id"]).status = status
            db.commit()
    ids = [saved(api, owner, p, examination_date=d, examination_time=t)[0]
           for d, t in (("2026-08-01", None), ("2026-08-01", "10:00"),
                        ("2026-08-01", "20:00"), ("2026-07-01", "23:00"))]
    saved(api, owner, other)
    with factory() as db:
        db.scalar(select(LabResult).where(LabResult.report_id == ids[2])).abnormal = "HIGH"
        db.commit()
    path = f"/api/v1/reports?health_profile_id={p}&page_size=2"
    first = api.get(path, headers=headers(owner)).json()
    second = api.get(path + "&page=2", headers=headers(owner)).json()
    assert [r["id"] for r in first["items"] + second["items"]] == [ids[2], ids[1], ids[0], ids[3]]
    assert first["total"] == 4 and first["has_more"] and not second["has_more"]
    assert first["items"][0]["item_count"] == 1 and first["items"][0]["abnormal_count"] == 1
    assert api.get('/api/v1/reports', headers=headers(owner)).status_code == 422
    for suffix in ("&page=0", "&page_size=101", "&page_size=0"):
        assert api.get(path + suffix, headers=headers(owner)).status_code == 422
    stranger = login(api, "stranger")
    assert api.get(path, headers=headers(stranger)).status_code == 404
    with factory() as db:
        db.get(HealthProfile, p).status = "DELETED"
        db.commit()
    assert api.get(path, headers=headers(owner)).status_code == 404


def test_detail_original_values_standard_names_assets_and_access(client, monkeypatch):
    api, factory = client
    owner = login(api, "detail")
    p = profile(api, owner)["id"]
    row, path = new_report(api, owner, p)
    old_ocr(factory, row["id"], decisions=("FINAL_AUTO",))
    workspace(api, owner, path)
    report_info(api, owner, path)
    add(api, owner, path, result="1 至 3（复查）")
    rid = api.post(path + '/commit', headers=headers(owner), json={}).json()["report_id"]
    asset_id = api.get(path, headers=headers(owner)).json()["assets"][0]["id"]
    root = f"/api/v1/reports/{rid}"
    data = api.get(root, headers=headers(owner)).json()
    assert [r["sequence_no"] for r in data["results"]] == [1, 2]
    assert data["results"][0]["metric_name"] == "原名称0"
    assert data["results"][0]["standard_metric"]["code"] == "ALT"
    assert data["results"][1]["result_text"] == "1 至 3（复查）"
    assert data["results"][1]["standard_metric"] is None
    assert data["results"][1]["abnormal"] is None
    assets = api.get(root + '/assets', headers=headers(owner)).json()
    assert set(assets[0]) == {"id", "page_no", "mime_type", "file_size"}
    monkeypatch.setattr(report_api, "preview_url", lambda key: 'https://signed.example/private')
    assert api.get(root + f'/assets/{asset_id}/preview', headers=headers(owner)).json()["expires_in"] == 300
    assert api.get(root + '/assets/wrong/preview', headers=headers(owner)).json()["code"] == 'REPORT_ASSET_NOT_FOUND'
    monkeypatch.setattr(report_api, "preview_url", lambda key: (_ for _ in ()).throw(ValueError()))
    assert api.get(root + f'/assets/{asset_id}/preview', headers=headers(owner)).json()["code"] == 'FILE_ACCESS_FAILED'
    assert api.get(root, headers=headers(owner)).status_code == 200
    assert api.patch(root, headers=headers(owner), json={}).status_code == 405
    stranger = login(api, 'access-other')
    target = profile(api, stranger)["id"]
    for suffix in ('', '/assets', f'/assets/{asset_id}/preview'):
        assert api.get(root + suffix, headers=headers(stranger)).status_code == 404
    assert api.post(root + '/migrate', headers=headers(stranger), json={"health_profile_id": target}).status_code == 404
    assert api.post(root + '/migrate', headers=headers(owner), json={"health_profile_id": target}).status_code == 404
    assert api.delete(root, headers=headers(stranger)).status_code == 404
    assert api.get(root, headers=headers(owner)).status_code == 200


@pytest.mark.parametrize('combined', [False, True])
def test_migrate_duplicate_ack_target_binding_noop_and_snapshots(client, combined):
    api, factory = client
    owner = login(api, "migrate")
    p = profile(api, owner)["id"]
    target = profile(api, owner, "父亲", "FATHER")["id"]
    third = profile(api, owner, "母亲", "MOTHER")["id"]
    info = {"report_no": None if combined else "DUP-1"}
    rid, iid = saved(api, owner, p, **info)
    old, _ = saved(api, owner, target, **info)
    saved(api, owner, third, **info)
    root = f"/api/v1/reports/{rid}"
    before = api.get(root, headers=headers(owner)).json()["results"]
    with factory() as db:
        source = [{c.name: getattr(x, c.name) for c in ConfirmationItem.__table__.columns}
                  for x in db.scalars(select(ConfirmationItem).where(ConfirmationItem.ingestion_id == iid))]
    duplicate = api.post(root + '/migrate', headers=headers(owner), json={"health_profile_id": target})
    assert duplicate.status_code == 409
    details = duplicate.json()["details"]
    assert [c['report_id'] for c in details['candidates']] == [old]
    assert api.get(root, headers=headers(owner)).json()["health_profile_id"] == p
    stale = api.post(root + '/migrate', headers=headers(owner),
                     json={"health_profile_id": third, "duplicate_acknowledgement": details['acknowledgement']})
    assert stale.status_code == 409
    moved = api.post(root + '/migrate', headers=headers(owner),
                     json={"health_profile_id": target, "duplicate_acknowledgement": details['acknowledgement']})
    assert moved.status_code == 200 and moved.json()["results"] == before
    with factory() as db:
        assert db.get(ReportIngestion, iid).health_profile_id == target
        assert all(x.health_profile_id == target for x in db.scalars(select(LabResult).where(LabResult.report_id == rid)))
        assert source == [{c.name: getattr(x, c.name) for c in ConfirmationItem.__table__.columns}
                          for x in db.scalars(select(ConfirmationItem).where(ConfirmationItem.ingestion_id == iid))]
        timestamp = db.get(LabReport, rid).updated_at
    noop = api.post(root + '/migrate', headers=headers(owner), json={"health_profile_id": target})
    assert noop.status_code == 200
    with factory() as db:
        assert db.get(LabReport, rid).updated_at == timestamp
    assert api.get(f'/api/v1/reports?health_profile_id={p}', headers=headers(owner)).json()["total"] == 0


@pytest.mark.parametrize('failure', ['cleanup', 'delete'])
def test_delete_rollback_keeps_entire_chain(client, failure):
    api, factory = client
    owner = login(api, 'rollback')
    rid, iid = saved(api, owner, profile(api, owner)["id"])
    def abort(*args):
        raise RuntimeError('synthetic transaction fault')
    if failure == 'cleanup':
        event.listen(FileCleanup, 'before_insert', abort)
    else:
        event.listen(factory.kw['bind'], 'before_cursor_execute',
                     blocker := lambda conn, cursor, statement, *args: abort() if statement.startswith('DELETE FROM report_assets') else None)
    try:
        assert api.delete(f'/api/v1/reports/{rid}', headers=headers(owner)).status_code == 500
    finally:
        if failure == 'cleanup':
            event.remove(FileCleanup, 'before_insert', abort)
        else:
            event.remove(factory.kw['bind'], 'before_cursor_execute', blocker)
    with factory() as db:
        assert db.get(LabReport, rid) and db.get(ReportIngestion, iid)
        assert db.scalar(select(func.count()).select_from(LabResult)) == 1
        assert db.scalar(select(func.count()).select_from(FileCleanup)) == 0


def test_delete_full_ocr_chain_cos_failure_retry_and_other_report(client, monkeypatch):
    api, factory = client
    owner = login(api, 'delete')
    p = profile(api, owner)["id"]
    row, path = new_report(api, owner, p)
    task_id = old_ocr(factory, row['id'], decisions=('FINAL_AUTO', 'FINAL_REVIEW'))
    data = workspace(api, owner, path)
    api.patch(path + '/confirmation/items/' + data['items'][1]['id'], headers=headers(owner), json={"resolution": 'REMOVED'})
    report_info(api, owner, path)
    rid = api.post(path + '/commit', headers=headers(owner), json={}).json()['report_id']
    with factory() as db:
        db.add(OcrTask(ingestion_id=row['id'], run_no=2, status='FAILED', input_manifest=[]))
        db.commit()
    other, _ = saved(api, owner, p)
    def fail(prefix):
        raise RuntimeError('synthetic COS unavailable')
    monkeypatch.setattr(cos, 'delete_prefix', fail)
    root = f'/api/v1/reports/{rid}'
    assert api.delete(root, headers=headers(owner)).status_code == 204
    with factory() as db:
        for model in (LabResult, ConfirmationItem, OcrResultItem, OcrTask, ReportAsset, UploadAuthorization, ReportIngestion):
            column = model.report_id if model is LabResult else model.id if model is ReportIngestion else model.ingestion_id if hasattr(model, 'ingestion_id') else model.ocr_task_id
            assert db.scalar(select(func.count()).select_from(model).where(column == (rid if model is LabResult else task_id if model is OcrResultItem else row['id']))) == 0
        assert db.get(LabReport, rid) is None
        cleanup = db.scalar(select(FileCleanup))
        assert cleanup.target_type == 'PREFIX' and cleanup.status == 'PENDING'
        assert cleanup.cos_object_key == f"users/{owner['user']['id']}/ingestions/{row['id']}/"
    for suffix in ('', '/assets', '/assets/wrong/preview'):
        assert api.get(root + suffix, headers=headers(owner)).status_code == 404
    assert api.delete(root, headers=headers(owner)).status_code == 404
    assert api.get(f'/api/v1/reports/{other}', headers=headers(owner)).status_code == 200
    assert row['id'] not in [i['id'] for i in api.get('/api/v1/ingestions', headers=headers(owner)).json()]
    seen = []
    monkeypatch.setattr(cos, 'delete_prefix', seen.append)
    cleanup_worker.run_once(factory)
    cleanup_worker.run_once(factory)
    assert len(seen) == 1
    with factory() as db:
        assert db.scalar(select(FileCleanup)).status == 'DONE'
        db.add(FileCleanup(cos_object_key='legacy/object'))
        db.commit()
    monkeypatch.setattr(cos, 'delete_object', seen.append)
    cleanup_worker.run_once(factory)
    assert seen[-1] == 'legacy/object'


def test_prefix_pagination_empty_and_retry(monkeypatch):
    class SDK:
        def __init__(self):
            self.objects = {f'prefix/{i:04d}' for i in range(2105)}
            self.calls = []
            self.fail = True
        def list_objects(self, **kw):
            self.calls.append(kw['Marker'])
            keys = sorted(k for k in self.objects if k > kw['Marker'])[:1000]
            return {'Contents': [{'Key': k} for k in keys], 'IsTruncated': len(keys) == 1000,
                    'NextMarker': keys[-1] if keys else ''}
        def delete_object(self, **kw):
            if self.fail and kw['Key'] == 'prefix/1001':
                raise RuntimeError('retry')
            self.objects.discard(kw['Key'])
    sdk = SDK()
    monkeypatch.setattr(cos, 'client', lambda: sdk)
    monkeypatch.setattr(cos, 'get_settings', lambda: SimpleNamespace(cos_bucket='synthetic'))
    with pytest.raises(RuntimeError):
        cos.delete_prefix('prefix/')
    sdk.fail = False
    cos.delete_prefix('prefix/')
    cos.delete_prefix('prefix/')
    assert not sdk.objects and len(sdk.calls) >= 5


def test_stable_ties_multi_page_assets_and_inactive_targets(client, monkeypatch):
    from datetime import UTC, datetime
    api, factory = client
    owner = login(api, 'ties')
    p = profile(api, owner)['id']
    target = profile(api, owner, '父亲', 'FATHER')['id']
    ids = [saved(api, owner, p)[0] for _ in range(3)]
    with factory() as db:
        for rid in ids:
            db.get(LabReport, rid).created_at = datetime(2026, 8, 1, tzinfo=UTC)
        db.get(HealthProfile, target).status = 'DELETED'
        db.commit()
    path = f'/api/v1/reports?health_profile_id={p}&page_size=1'
    actual = [api.get(path + f'&page={i}', headers=headers(owner)).json()['items'][0]['id'] for i in (1, 2, 3)]
    assert actual == sorted(ids, reverse=True)
    assert api.post(f'/api/v1/reports/{ids[0]}/migrate', headers=headers(owner), json={'health_profile_id': target}).status_code == 404
    # Source assets, unlike formal results, stay in their ingestion and preserve page order.
    with factory() as db:
        iid = db.get(LabReport, ids[0]).source_ingestion_id
        db.add(ReportAsset(ingestion_id=iid, cos_object_key='synthetic/page2', page_no=2, mime_type='image/png', file_size=123))
        db.commit()
    pages = api.get(f'/api/v1/reports/{ids[0]}/assets', headers=headers(owner)).json()
    assert [a['page_no'] for a in pages] == [1, 2]
    other_pages = api.get(f'/api/v1/reports/{ids[1]}/assets', headers=headers(owner)).json()
    assert api.get(f"/api/v1/reports/{ids[0]}/assets/{other_pages[0]['id']}/preview", headers=headers(owner)).status_code == 404


def test_immediate_cos_success_and_log_privacy(client, monkeypatch, caplog):
    api, factory = client
    owner = login(api, 'immediate')
    rid, _iid = saved(api, owner, profile(api, owner)['id'])
    seen = []
    monkeypatch.setattr(cos, 'delete_prefix', seen.append)
    assert api.delete(f'/api/v1/reports/{rid}', headers=headers(owner)).status_code == 204
    with factory() as db:
        cleanup = db.scalar(select(FileCleanup))
        assert cleanup.status == 'DONE'
        assert seen == [cleanup.cos_object_key]
        cleanup.status = 'PENDING'
        db.commit()
    monkeypatch.setattr(cos, 'delete_prefix', lambda key: (_ for _ in ()).throw(RuntimeError('合成医疗敏感全文')))
    cleanup_worker.run_once(factory)
    assert '合成医疗敏感全文' not in caplog.text
    assert seen[0] not in caplog.text
    with factory() as db:
        assert db.scalar(select(FileCleanup)).status == 'PENDING'


def test_ocr_report_migration_preserves_every_source_snapshot(client):
    api, factory = client
    owner = login(api, 'source-snapshot')
    p = profile(api, owner)['id']
    target = profile(api, owner, '父亲', 'FATHER')['id']
    row, path = new_report(api, owner, p)
    tid = old_ocr(factory, row['id'], decisions=('FINAL_AUTO',))
    workspace(api, owner, path)
    report_info(api, owner, path)
    rid = api.post(path + '/commit', headers=headers(owner), json={}).json()['report_id']
    def snapshots():
        with factory() as db:
            return {model.__tablename__: [{c.name: getattr(r, c.name) for c in model.__table__.columns}
                    for r in db.scalars(select(model).order_by(model.id))]
                    for model in (ConfirmationItem, OcrResultItem, OcrTask, ReportAsset)}
    before = snapshots()
    detail_before = api.get(f'/api/v1/reports/{rid}', headers=headers(owner)).json()
    moved = api.post(f'/api/v1/reports/{rid}/migrate', headers=headers(owner), json={'health_profile_id': target})
    assert moved.status_code == 200 and snapshots() == before
    assert moved.json()['results'] == detail_before['results']
    for field in ('hospital_name', 'examination_date', 'examination_time', 'report_no', 'report_category'):
        assert moved.json()[field] == detail_before[field]
    with factory() as db:
        assert db.get(OcrTask, tid).ingestion_id == row['id']


@pytest.mark.parametrize('committed', [False, True])
def test_failed_asset_delete_cleanup_preserves_referenced_original(client, monkeypatch, committed):
    api, factory = client
    owner = login(api, 'referenced-original')
    profile_id = profile(api, owner)['id']
    draft = ingestion(api, owner, profile_id)
    key, page = asset(api, owner, draft['id'])
    path = f"/api/v1/ingestions/{draft['id']}"

    def fail_delete(_key):
        raise HTTPException(502, 'COS_DELETE_FAILED')

    monkeypatch.setattr(business, 'delete_object', fail_delete)
    assert api.delete(path + f"/assets/{page['id']}", headers=headers(owner)).status_code == 502
    if committed:
        assert api.post(path + '/manual', headers=headers(owner)).status_code == 200
        report_info(api, owner, path)
        add(api, owner, path)
        response = api.post(path + '/commit', headers=headers(owner), json={})
        assert response.status_code == 200
        report_id = response.json()['report_id']
    deletes = []
    monkeypatch.setattr(cos, 'delete_object', deletes.append)
    cleanup_worker.run_once(factory)
    cleanup_worker.run_once(factory)
    assert deletes == []
    with factory() as db:
        assert db.get(ReportAsset, page['id']).cos_object_key == key
        cleanup = db.scalar(select(FileCleanup).where(FileCleanup.cos_object_key == key))
        assert cleanup.target_type == 'OBJECT' and cleanup.status == 'PENDING'
    assert api.get(path + f"/assets/{page['id']}/preview", headers=headers(owner)).status_code == 200
    if committed:
        assert api.get(f'/api/v1/reports/{report_id}/assets', headers=headers(owner)).json()[0]['id'] == page['id']
    else:
        # Only the explicit user retry removes the still-referenced asset.
        user_deletes = []
        monkeypatch.setattr(business, 'delete_object', user_deletes.append)
        assert api.delete(path + f"/assets/{page['id']}", headers=headers(owner)).status_code == 200
        assert user_deletes == [key]
        cleanup_worker.run_once(factory)
        assert deletes == []
        with factory() as db:
            assert db.get(ReportAsset, page['id']) is None
            assert db.scalar(select(FileCleanup).where(FileCleanup.cos_object_key == key)).status == 'DONE'


def test_unreferenced_object_cleanup_failure_retry_and_idempotence(client, monkeypatch):
    _api, factory = client
    with factory() as db:
        row = FileCleanup(cos_object_key='synthetic/unreferenced-original', target_type='OBJECT')
        db.add(row)
        db.commit()
        cleanup_id = row.id
    deletes = []

    def fail_delete(key):
        deletes.append(key)
        raise RuntimeError('synthetic unavailable')

    monkeypatch.setattr(cos, 'delete_object', fail_delete)
    cleanup_worker.run_once(factory)
    with factory() as db:
        assert db.get(FileCleanup, cleanup_id).status == 'PENDING'
    monkeypatch.setattr(cos, 'delete_object', deletes.append)
    cleanup_worker.run_once(factory)
    cleanup_worker.run_once(factory)
    assert deletes == ['synthetic/unreferenced-original'] * 2
    with factory() as db:
        assert db.get(FileCleanup, cleanup_id).status == 'DONE'
