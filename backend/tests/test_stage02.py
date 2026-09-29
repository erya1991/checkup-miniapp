from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1 import business
from app.core import auth
from app.core import cos as cos_service
from app.db.base import Base
from app.main import app
from app.models import FileCleanup, HealthProfile, ReportAsset, ReportIngestion, User


@pytest.fixture
def client(monkeypatch):
    engine = create_engine("sqlite+pysqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def session():
        with factory() as db:
            yield db

    app.dependency_overrides[auth.db_session] = session
    monkeypatch.setattr(auth, "get_settings", lambda: SimpleNamespace(jwt_secret="test-secret-longer-than-32-bytes-okay"))
    monkeypatch.setattr(business, "exchange_wechat_code", lambda code: code)
    monkeypatch.setattr(business, "upload_credential", lambda key: {
        "object_key": key, "bucket": "private-123", "region": "ap-test",
        "start_time": 1, "expired_time": 2,
        "credentials": {"tmpSecretId": "temporary", "tmpSecretKey": "temporary",
                        "sessionToken": "temporary"},
    })
    monkeypatch.setattr(business, "object_metadata", lambda key: {"Content-Length": "123"})
    monkeypatch.setattr(business, "preview_url", lambda key: "https://signed.example/test")
    monkeypatch.setattr(business, "delete_object", lambda key: None)
    with TestClient(app) as api:
        yield api, factory
    app.dependency_overrides.clear()
    engine.dispose()


def login(api, name):
    response = api.post("/api/v1/auth/wechat", json={"code": name})
    assert response.status_code == 200, response.text
    return response.json()


def headers(auth_result):
    return {"Authorization": f"Bearer {auth_result['access_token']}"}


def profile(api, auth_result, name="本人", relation="SELF"):
    response = api.post("/api/v1/health-profiles", headers=headers(auth_result),
                        json={"display_name": name, "relation": relation})
    assert response.status_code == 201, response.text
    return response.json()


def ingestion(api, auth_result, profile_id):
    response = api.post("/api/v1/ingestions", headers=headers(auth_result),
                        json={"health_profile_id": profile_id, "mode": "OCR"})
    assert response.status_code == 201, response.text
    return response.json()


def asset(api, auth_result, ingestion_id):
    h = headers(auth_result)
    authorization = api.post(f"/api/v1/ingestions/{ingestion_id}/upload-authorizations",
                             headers=h, json={"mime_type": "image/jpeg"})
    assert authorization.status_code == 200, authorization.text
    key = authorization.json()["object_key"]
    registered = api.post(f"/api/v1/ingestions/{ingestion_id}/assets", headers=h,
                          json={"object_key": key, "mime_type": "image/jpeg", "file_size": 123})
    assert registered.status_code == 201, registered.text
    return key, registered.json()


def test_login_new_and_existing_user_and_auth(client):
    api, factory = client
    first = login(api, "wechat-a")
    second = login(api, "wechat-a")
    assert first["user"]["id"] == second["user"]["id"]
    with factory() as db:
        assert len(db.scalars(select(User)).all()) == 1
    for path in ("/api/v1/me", "/api/v1/health-profiles", "/api/v1/ingestions"):
        assert api.get(path).status_code == 401
    assert api.get("/api/v1/me", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_profiles_crud_default_and_cross_user(client):
    api, factory = client
    a, b = login(api, "a"), login(api, "b")
    own = profile(api, a)
    father = profile(api, a, "父亲", "FATHER")
    profile(api, a, "母亲", "MOTHER")
    foreign = profile(api, b, "其他", "OTHER")
    assert api.get("/api/v1/me", headers=headers(a)).json()["default_health_profile_id"] == own["id"]
    assert len(api.get("/api/v1/health-profiles", headers=headers(a)).json()) == 3
    switched = api.put("/api/v1/me/default-health-profile", headers=headers(a),
                       json={"health_profile_id": father["id"]})
    assert switched.json()["default_health_profile_id"] == father["id"]
    edited = api.patch(f"/api/v1/health-profiles/{father['id']}", headers=headers(a),
                       json={"display_name": "父亲新名", "relation": "OTHER", "gender": "MALE"})
    assert edited.json()["display_name"] == "父亲新名"
    assert edited.json()["relation"] == "OTHER"
    assert api.get(f"/api/v1/health-profiles/{father['id']}", headers=headers(a)).json()["gender"] == "MALE"
    for method in (api.get, api.patch, api.delete):
        kwargs = {"json": {"display_name": "bad"}} if method == api.patch else {}
        assert method(f"/api/v1/health-profiles/{foreign['id']}", headers=headers(a),
                      **kwargs).status_code == 404
    assert api.put("/api/v1/me/default-health-profile", headers=headers(a),
                   json={"health_profile_id": foreign["id"]}).status_code == 404
    assert api.delete(f"/api/v1/health-profiles/{father['id']}", headers=headers(a)).status_code == 204
    with factory() as db:
        assert db.get(HealthProfile, father["id"]).status == "DELETED"


def test_ingestion_assets_ready_order_delete_and_resume(client):
    api, factory = client
    a, b = login(api, "a"), login(api, "b")
    own, foreign = profile(api, a, "父亲", "FATHER"), profile(api, b)
    assert api.post("/api/v1/ingestions", headers=headers(a),
                    json={"health_profile_id": foreign["id"]}).status_code == 404
    i = ingestion(api, a, own["id"])
    assert i["status"] == "UPLOADING"
    keys_assets = [asset(api, a, i["id"]) for _ in range(3)]
    keys = [pair[0] for pair in keys_assets]
    assert len(set(keys)) == 3
    assert all(key.split("/")[-1].endswith(".jpg") for key in keys)
    assert all(key.startswith(f"users/{a['user']['id']}/ingestions/{i['id']}/original/") for key in keys)
    resumed = api.get(f"/api/v1/ingestions/{i['id']}", headers=headers(a)).json()
    assert resumed["status"] == "READY"
    assert [row["page_no"] for row in resumed["assets"]] == [1, 2, 3]
    ids = [pair[1]["id"] for pair in keys_assets]
    changed = api.put(f"/api/v1/ingestions/{i['id']}/assets/order", headers=headers(a),
                      json={"asset_ids": [ids[2], ids[0], ids[1]]})
    assert changed.status_code == 200, changed.text
    assert [row["id"] for row in changed.json()["assets"]] == [ids[2], ids[0], ids[1]]
    assert api.put(f"/api/v1/ingestions/{i['id']}/assets/order", headers=headers(a),
                   json={"asset_ids": [ids[0]]}).status_code == 422
    assert api.get(f"/api/v1/ingestions/{i['id']}/assets/{ids[0]}/preview",
                   headers=headers(a)).json()["url"].startswith("https://signed")
    for asset_id in ids:
        assert api.delete(f"/api/v1/ingestions/{i['id']}/assets/{asset_id}",
                          headers=headers(a)).status_code == 200
    assert api.get(f"/api/v1/ingestions/{i['id']}", headers=headers(a)).json()["status"] == "UPLOADING"
    with factory() as db:
        assert not db.scalars(select(ReportAsset)).all()
        assert db.get(ReportIngestion, i["id"]).health_profile_id == own["id"]


def test_upload_verification_and_cross_user_isolation(client, monkeypatch):
    api, factory = client
    a, b = login(api, "a"), login(api, "b")
    own = profile(api, a)
    foreign = profile(api, b)
    i = ingestion(api, b, foreign["id"])
    path = f"/api/v1/ingestions/{i['id']}"
    assert api.get(path, headers=headers(a)).status_code == 404
    assert api.post(path + "/upload-authorizations", headers=headers(a),
                    json={"mime_type": "image/jpeg"}).status_code == 404
    assert api.post(path + "/assets", headers=headers(a), json={
        "object_key": "fake", "mime_type": "image/jpeg", "file_size": 123}).status_code == 404
    assert api.put(path + "/assets/order", headers=headers(a),
                   json={"asset_ids": []}).status_code == 404
    key, row = asset(api, b, i["id"])
    assert api.delete(path + f"/assets/{row['id']}", headers=headers(a)).status_code == 404
    assert api.get(path + f"/assets/{row['id']}/preview", headers=headers(a)).status_code == 404
    own_i = ingestion(api, a, own["id"])
    assert api.post(f"/api/v1/ingestions/{own_i['id']}/assets", headers=headers(a), json={
        "object_key": key, "mime_type": "image/jpeg", "file_size": 123}).status_code == 409
    authorization = api.post(f"/api/v1/ingestions/{own_i['id']}/upload-authorizations",
                             headers=headers(a), json={"mime_type": "image/jpeg"}).json()
    key = authorization["object_key"]
    assert "cos_secret_key" not in authorization
    monkeypatch.setattr(business, "object_metadata", lambda key: {"Content-Length": "99"})
    assert api.post(f"/api/v1/ingestions/{own_i['id']}/assets", headers=headers(a), json={
        "object_key": key, "mime_type": "image/jpeg", "file_size": 123}).status_code == 409
    assert api.get(f"/api/v1/ingestions/{own_i['id']}", headers=headers(a)).json()["status"] == "UPLOADING"
    monkeypatch.setattr(business, "object_metadata", lambda key: {"content-length": "123"})
    assert api.post(f"/api/v1/ingestions/{own_i['id']}/assets", headers=headers(a), json={
        "object_key": key, "mime_type": "image/jpeg", "file_size": 123}).status_code == 201
    with factory() as db:
        assert len(db.scalars(select(ReportAsset)).all()) == 2


def test_cos_delete_failure_keeps_asset_and_cleanup_record(client, monkeypatch):
    api, factory = client
    user = login(api, "a")
    p = profile(api, user)
    i = ingestion(api, user, p["id"])
    key, row = asset(api, user, i["id"])

    def fail_delete(_key):
        raise HTTPException(502, "COS_DELETE_FAILED")

    monkeypatch.setattr(business, "delete_object", fail_delete)
    response = api.delete(f"/api/v1/ingestions/{i['id']}/assets/{row['id']}",
                          headers=headers(user))
    assert response.status_code == 502
    with factory() as db:
        assert db.get(ReportAsset, row["id"]) is not None
        cleanup = db.scalar(select(FileCleanup).where(FileCleanup.cos_object_key == key))
        assert cleanup.status == "PENDING"


def test_sts_policy_is_one_object_put_only(monkeypatch):
    captured = {}

    class FakeSts:
        def __init__(self, options):
            captured.update(options)

        def get_credential(self):
            return {"credentials": {"tmpSecretId": "temporary", "tmpSecretKey": "temporary",
                                     "sessionToken": "temporary"}, "startTime": 1, "expiredTime": 2}

    monkeypatch.setattr(cos_service, "Sts", FakeSts)
    monkeypatch.setattr(cos_service, "get_settings", lambda: SimpleNamespace(
        cos_secret_id="permanent-id", cos_secret_key="permanent-key",
        cos_bucket="private-123456", cos_region="ap-test"))
    key = "users/u/ingestions/i/original/x.jpg"
    result = cos_service.upload_credential(key)
    assert captured["allow_prefix"] == key
    assert captured["allow_actions"] == ["name/cos:PutObject"]
    assert captured["duration_seconds"] == 900
    assert result["object_key"] == key
    assert "permanent-key" not in str(result)
