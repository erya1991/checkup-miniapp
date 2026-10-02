"""Stage 07 safety contracts with synthetic data only."""
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
import pytest
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError
from test_stage02 import headers, login, profile
from test_stage04 import client as stage04_client
from test_stage04 import machine_snapshot, new_report, old_ocr, patch, report_info, workspace
from test_stage06 import favorite, get, metric_id, saved

from app import confirmation as confirmation_service
from app import ocr_worker
from app.core import admin_auth
from app.core.admin_auth import password_hash, verify_password
from app.metric_identity import normalize_name, resolve_exact
from app.models import (
    ConfirmationItem,
    LabResult,
    MetricAlias,
    OcrResultItem,
    OcrTask,
)
from app.ocr_pipeline import map_row
from app.ocr_queue import claim


@pytest.fixture
def client(monkeypatch):
    cfg = SimpleNamespace(admin_username="synthetic-admin", admin_password_hash=password_hash("synthetic"),
                          admin_jwt_secret="independent-admin-test-secret-32-plus",
                          jwt_secret="test-secret-longer-than-32-bytes-okay")
    monkeypatch.setattr(admin_auth, "get_settings", lambda: cfg)
    yield from stage04_client.__wrapped__(monkeypatch)


def admin(api):
    response = api.post("/api/v1/admin/auth/login", json={"username": "synthetic-admin", "password": "synthetic"})
    assert response.status_code == 200, response.text
    return headers(response.json())


def create(api, auth, code="TEST07", name="合成新指标", **extra):
    response = api.post("/api/v1/admin/standard-metrics", headers=auth,
                        json={"code": code, "name": name, **extra})
    assert response.status_code == 201, response.text
    return response.json()


def alias(api, auth, target, raw="合成别名", kind="SYNONYM"):
    response = api.post("/api/v1/admin/metric-aliases", headers=auth,
                        json={"standard_metric_id": target, "alias": raw, "alias_type": kind})
    assert response.status_code == 201, response.text
    return response.json()


def change(api, auth, resource, resource_id, **values):
    return api.patch(f"/api/v1/admin/{resource}/{resource_id}", headers=auth, json=values)


def snapshot(factory, entity):
    with factory() as db:
        return [{c.name: getattr(row, c.name) for c in entity.__table__.columns}
                for row in db.scalars(select(entity).order_by(entity.id))]


@pytest.mark.parametrize("raw,expected", [
    (" ＊ＡＬＴ ", "alt"), ("*Γ-ɣ_γ", "γγγ"), (" ALT.[x]/·【甲】（乙） ", "altx甲乙"),
    ("\t谷 丙 转 氨 酶\n", "谷丙转氨酶"), (None, ""), ("***--", ""),
])
def test_normalization(raw, expected):
    assert normalize_name(raw) == expected


def test_exact_priority_ambiguity_and_no_fuzzy():
    dictionary = ({"ALT": "a"}, {"ast": {"b"}, "重复": {"a", "b"}}, {"谷丙": "b"})
    assert resolve_exact(dictionary, "ALT", "谷丙") == ("a", True)
    assert resolve_exact(dictionary, None, "AST") == ("b", False)
    assert resolve_exact(dictionary, "MISSING", "谷丙") == ("b", False)
    assert resolve_exact(dictionary, None, "重复") == (None, False)
    assert resolve_exact(dictionary, None, "谷丙酶") == (None, False)


def test_password_hash_contract():
    encoded = password_hash("synthetic-password")
    assert verify_password("synthetic-password", encoded)
    assert not verify_password("wrong", encoded)
    assert not verify_password("x", "malformed")


def test_auth_isolation_expiry_configuration_and_validation_privacy(client, monkeypatch, caplog):
    api, _ = client
    assert api.get("/api/v1/admin/me").json()["code"] == "ADMIN_AUTH_REQUIRED"
    for username, password in [("synthetic-admin", "wrong"), ("wrong", "synthetic")]:
        response = api.post("/api/v1/admin/auth/login", json={"username": username, "password": password})
        assert response.json()["code"] == "ADMIN_AUTH_INVALID"
    auth = admin(api)
    assert api.get("/api/v1/admin/me", headers=auth).json()["scope"] == "admin"
    owner = login(api, "ordinary")
    for endpoint in ("me", "standard-metrics", "metric-aliases", "ocr-metric-issues", "ocr-tasks"):
        assert api.get("/api/v1/admin/" + endpoint, headers=headers(owner)).status_code == 401
    for endpoint in ("health-profiles", "reports", "profile-metrics"):
        assert api.get("/api/v1/" + endpoint, headers=auth).status_code == 401
    cfg = admin_auth.get_settings()
    token = jwt.encode({"sub": cfg.admin_username, "scope": "admin", "aud": "checkup-admin",
                        "iat": datetime.now(UTC) - timedelta(days=1),
                        "exp": datetime.now(UTC) - timedelta(hours=1)}, cfg.admin_jwt_secret, algorithm="HS256")
    assert api.get("/api/v1/admin/me", headers={"Authorization": "Bearer " + token}).status_code == 401
    sensitive = "private-password" * 200
    response = api.post("/api/v1/admin/auth/login", json={"username": "x", "password": sensitive})
    assert response.status_code == 422 and sensitive not in response.text
    assert "synthetic" not in caplog.text and auth["Authorization"] not in caplog.text
    cfg.admin_jwt_secret = cfg.jwt_secret
    assert api.post("/api/v1/admin/auth/login", json={"username": "x", "password": "x"}).status_code == 503


def test_metric_crud_filter_code_immutable_and_no_delete(client):
    api, _ = client
    auth = admin(api)
    metric = create(api, auth, code=" test07 ", category="其他")
    assert metric["code"] == "TEST07" and metric["status"] == "ACTIVE"
    for code in (None, "TEST07", "NEW"):
        assert change(api, auth, "standard-metrics", metric["id"], code=code).json()["code"] == "STANDARD_METRIC_CODE_IMMUTABLE"
    response = api.post("/api/v1/admin/standard-metrics", headers=auth, json={"code": "test07", "name": "重复"})
    assert response.json()["code"] == "STANDARD_METRIC_CODE_CONFLICT"
    for key in ("code", "name"):
        response = api.post("/api/v1/admin/standard-metrics", headers=auth, json={"code": "X", "name": "X", key: " "})
        assert response.status_code == 422
    changed = change(api, auth, "standard-metrics", metric["id"], name="新展示名", category=None).json()
    assert changed["name"] == "新展示名" and changed["category"] is None
    assert changed["updated_at"] != metric["updated_at"]
    for status in ("INACTIVE", "ACTIVE"):
        assert change(api, auth, "standard-metrics", metric["id"], status=status).json()["status"] == status
    listing = api.get("/api/v1/admin/standard-metrics", headers=auth, params={"q": "TEST07", "page_size": 1}).json()
    assert listing["total"] == 1 and listing["items"][0]["code"] == "TEST07"
    assert api.delete(f"/api/v1/admin/standard-metrics/{metric['id']}", headers=auth).status_code == 405
    assert api.post("/api/v1/admin/standard-metrics", headers=auth,
                    json={"code": "ß" * 64, "name": "大写扩展长度"}).json()["code"] == "INVALID_STANDARD_METRIC"


def test_manual_alias_text_never_auto_binds_and_new_metric_does_not_reinitialize(client):
    api, factory = client
    auth = admin(api)
    owner = login(api, "manual-exact07")
    p = profile(api, owner)["id"]
    alias(api, auth, metric_id(factory, "ALT"), "合成指标")
    saved(api, factory, owner, p, [{"result": "5.1", "metric": None}])
    assert snapshot(factory, LabResult)[0]["standard_metric_id"] is None
    report, path = new_report(api, owner, p)
    old_ocr(factory, report["id"], decisions=("FINAL_REVIEW",), codes=["FUTURE07"])
    old = workspace(api, owner, path)["items"][0]
    create(api, auth, code="FUTURE07", name="未来主数据")
    assert workspace(api, owner, path)["items"][0] == old


def test_canonical_name_code_normalization_exact_without_fuzzy(client):
    api, factory = client
    owner = login(api, "canonical07")
    report, path = new_report(api, owner, profile(api, owner)["id"])
    task = old_ocr(factory, report["id"], decisions=("FINAL_REVIEW",) * 3, codes=[None] * 3)
    with factory() as db:
        rows = list(db.scalars(select(OcrResultItem).where(OcrResultItem.ocr_task_id == task)
                               .order_by(OcrResultItem.sequence_no)))
        rows[0].raw_metric = "＊ＡＬＴ"
        rows[1].raw_metric = "丙氨酸 氨基转移酶"
        rows[2].raw_metric = "丙氨酸氨基转移酶未命中"
        db.commit()
    before = machine_snapshot(factory, task)
    items = workspace(api, owner, path)["items"]
    assert [i["standard_metric_id"] for i in items] == [metric_id(factory, "ALT")] * 2 + [None]
    assert all(i["review_status"] == "PENDING" for i in items)
    assert machine_snapshot(factory, task) == before


@pytest.mark.parametrize("kind", ["SYNONYM", "ABBREVIATION", "OCR_VARIANT", "HOSPITAL_NAME"])
def test_alias_management_normalized_uniqueness_and_target_immutable(client, kind):
    api, factory = client
    auth = admin(api)
    target = metric_id(factory, "ALT")
    row = alias(api, auth, target, " ＊ＡＬＴ-Ｖａｒ ", kind)
    assert row["alias"] == " ＊ＡＬＴ-Ｖａｒ " and row["normalized_alias"] == "altvar"
    response = api.post("/api/v1/admin/metric-aliases", headers=auth,
                        json={"standard_metric_id": metric_id(factory, "AST"), "alias": "alt.var", "alias_type": kind})
    assert response.json()["code"] == "METRIC_ALIAS_DUPLICATE"
    assert change(api, auth, "metric-aliases", row["id"], standard_metric_id=target).json()["code"] == "METRIC_ALIAS_TARGET_IMMUTABLE"
    updated = change(api, auth, "metric-aliases", row["id"], alias="新别名", alias_type="OCR_VARIANT").json()
    assert updated["normalized_alias"] == "新别名"
    assert change(api, auth, "metric-aliases", row["id"], status="INACTIVE").status_code == 200
    replacement = alias(api, auth, target, "新 别 名")
    assert change(api, auth, "metric-aliases", row["id"], status="ACTIVE").json()["code"] == "METRIC_ALIAS_DUPLICATE"
    assert change(api, auth, "metric-aliases", replacement["id"], status="INACTIVE").status_code == 200
    assert change(api, auth, "metric-aliases", row["id"], status="ACTIVE").status_code == 200
    assert api.delete(f"/api/v1/admin/metric-aliases/{row['id']}", headers=auth).status_code == 405
    with factory() as db:
        db.add(MetricAlias(standard_metric_id=target, alias="新别名", normalized_alias="新别名",
                           alias_type="SYNONYM", status="ACTIVE"))
        with pytest.raises(IntegrityError):
            db.commit()


def test_namespace_both_directions_restore_and_inactive_target(client):
    api, factory = client
    auth = admin(api)
    target = metric_id(factory, "ALT")
    for raw in ("ALT", "AST", "丙氨酸氨基转移酶"):
        response = api.post("/api/v1/admin/metric-aliases", headers=auth,
                            json={"standard_metric_id": target, "alias": raw, "alias_type": "SYNONYM"})
        assert response.json()["code"] == "METRIC_ALIAS_CONFLICT"
    alias(api, auth, target, "future-code")
    for code, name in [("FUTURECODE", "其他"), ("OTHER", "future code")]:
        assert api.post("/api/v1/admin/standard-metrics", headers=auth, json={"code": code, "name": name}).json()["code"] == "METRIC_ALIAS_CONFLICT"
    item = create(api, auth, code="REACT07", name="旧名")
    assert change(api, auth, "standard-metrics", item["id"], name="future code").json()["code"] == "METRIC_ALIAS_CONFLICT"
    change(api, auth, "standard-metrics", item["id"], status="INACTIVE")
    alias(api, auth, target, "REACT07")
    assert change(api, auth, "standard-metrics", item["id"], status="ACTIVE").json()["code"] == "METRIC_ALIAS_CONFLICT"
    response = api.post("/api/v1/admin/metric-aliases", headers=auth,
                        json={"standard_metric_id": item["id"], "alias": "INACTIVE TARGET", "alias_type": "SYNONYM"})
    assert response.json()["code"] == "METRIC_ALIAS_TARGET_INACTIVE"


def test_search_canonical_dedup_and_inactive(client):
    api, factory = client
    auth = admin(api)
    owner = login(api, "search07")
    mid = metric_id(factory, "ALT")
    a = alias(api, auth, mid, "特殊检验一")
    alias(api, auth, mid, "特殊检验二")
    def search(query):
        return api.get("/api/v1/standard-metrics", headers=headers(owner), params={"q": query}).json()
    assert len(search("特殊检验")) == 1 and search("特殊检验")[0]["id"] == mid
    assert search("ALT") and search("丙氨酸")
    change(api, auth, "metric-aliases", a["id"], status="INACTIVE")
    assert search("特殊检验一") == []
    change(api, auth, "standard-metrics", mid, status="INACTIVE")
    assert search("特殊检验二") == [] and search("ALT") == []


def test_resolver_review_auto_missing_code_keep_original_and_snapshot(client):
    api, factory = client
    auth = admin(api)
    owner = login(api, "resolver07")
    report, path = new_report(api, owner, profile(api, owner)["id"])
    task = old_ocr(factory, report["id"], decisions=("FINAL_REVIEW", "FINAL_REVIEW", "FINAL_AUTO", "FINAL_AUTO"),
                   codes=[None, "ALT", None, "ALT"])
    with factory() as db:
        rows = list(db.scalars(select(OcrResultItem).where(OcrResultItem.ocr_task_id == task).order_by(OcrResultItem.sequence_no)))
        for row in rows:
            row.raw_metric = "新 exact 别名"
        db.commit()
    alias(api, auth, metric_id(factory, "AST"), "新exact别名")
    before = machine_snapshot(factory, task)
    items = workspace(api, owner, path)["items"]
    assert [i["standard_metric_id"] for i in items] == [metric_id(factory, code) for code in ("AST", "ALT", "AST", "ALT")]
    assert [i["standard_metric"]["code"] for i in items] == ["AST", "ALT", "AST", "ALT"]
    assert items[0]["standard_metric"] == {"id": metric_id(factory, "AST"), "code": "AST",
                                            "name": "天门冬氨酸氨基转移酶", "status": "ACTIVE"}
    assert [i["review_status"] for i in items] == ["PENDING", "PENDING", "PENDING", "RESOLVED"]
    assert items[0]["resolution"] is None
    report_info(api, owner, path)
    assert api.post(path + "/commit", headers=headers(owner)).json()["code"] == "REVIEW_PENDING"
    for item in items[:3]:
        response = patch(api, owner, path, item["id"], resolution="KEEP_ORIGINAL_NAME")
        assert response.status_code == 200
        cleared = next(i for i in response.json()["items"] if i["id"] == item["id"])
        assert cleared["standard_metric_id"] is None and cleared["standard_metric"] is None
    assert api.post(path + "/commit", headers=headers(owner)).status_code == 200
    assert machine_snapshot(factory, task) == before
    assert [r["standard_metric_id"] for r in snapshot(factory, LabResult)].count(None) == 3


def test_workspace_canonical_display_is_batch_loaded_without_recomputing(client, monkeypatch):
    api, factory = client
    auth = admin(api)
    owner = login(api, "canonical-display07")
    report, path = new_report(api, owner, profile(api, owner)["id"])
    task = old_ocr(factory, report["id"], decisions=("FINAL_REVIEW",) * 4,
                   codes=["ALT", "AST", "ALT", None])
    first = workspace(api, owner, path)
    assert first["items"][3]["standard_metric"] is None
    before_items = snapshot(factory, ConfirmationItem)
    before_machine = machine_snapshot(factory, task)
    assert change(api, auth, "standard-metrics", metric_id(factory, "ALT"), name="当前 ALT 名称").status_code == 200

    def forbidden_resolver(*args, **kwargs):
        pytest.fail("existing workspace must not run the resolver for display")

    monkeypatch.setattr(confirmation_service, "resolve_exact", forbidden_resolver)
    statements = []

    def record(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT") and "FROM standard_metrics" in statement:
            statements.append(statement)

    engine = factory.kw["bind"]
    event.listen(engine, "before_cursor_execute", record)
    try:
        second = workspace(api, owner, path)
    finally:
        event.remove(engine, "before_cursor_execute", record)
    assert len(statements) == 1  # one batch lookup, including repeated metric IDs
    assert [i["id"] for i in second["items"]] == [i["id"] for i in first["items"]]
    assert second["pending_count"] == 4
    for item in second["items"]:
        assert item["review_status"] == "PENDING" and item["resolution"] is None
        if item["standard_metric_id"]:
            assert item["standard_metric"]["id"] == item["standard_metric_id"]
    assert second["items"][0]["standard_metric"]["name"] == "当前 ALT 名称"
    assert second["items"][2]["standard_metric"]["name"] == "当前 ALT 名称"
    assert second["items"][3]["standard_metric"] is None
    assert snapshot(factory, ConfirmationItem) == before_items
    assert machine_snapshot(factory, task) == before_machine


def test_old_workspace_never_recomputed_and_pending_blocks_deactivation(client):
    api, factory = client
    auth = admin(api)
    owner = login(api, "old07")
    report, path = new_report(api, owner, profile(api, owner)["id"])
    task = old_ocr(factory, report["id"], decisions=("FINAL_REVIEW",), codes=[None])
    before = machine_snapshot(factory, task)
    old = workspace(api, owner, path)["items"][0]
    assert old["standard_metric_id"] is None
    alias(api, auth, metric_id(factory, "ALT"), "原名称0")
    assert workspace(api, owner, path)["items"][0] == old
    assert patch(api, owner, path, old["id"], resolution="STANDARD_METRIC_SELECTED",
                 standard_metric_id=metric_id(factory, "ALT")).status_code == 200
    response = change(api, auth, "standard-metrics", metric_id(factory, "ALT"), status="INACTIVE")
    assert response.json()["code"] == "STANDARD_METRIC_IN_USE_BY_PENDING_CONFIRMATION"
    assert response.json()["details"] == {"pending_count": 1}
    assert machine_snapshot(factory, task) == before


def test_formal_history_rename_inactive_favorite_and_no_backfill(client):
    api, factory = client
    auth = admin(api)
    owner = login(api, "history07")
    p = profile(api, owner)["id"]
    mid = metric_id(factory)
    rid = saved(api, factory, owner, p, [{"result": "5.1", "unit": "U"}, {"result": "陰性", "metric": None}])
    assert favorite(api, owner, p, mid)
    before = snapshot(factory, LabResult)
    confirmation = snapshot(factory, ConfirmationItem)
    alias(api, auth, mid, "合成指标")
    assert change(api, auth, "standard-metrics", mid, name="当前统一新名称").status_code == 200
    assert change(api, auth, "standard-metrics", mid, status="INACTIVE").status_code == 200
    info = get(api, owner, p, mid)
    assert info["standard_metric"]["name"] == "当前统一新名称" and info["is_favorite"]
    assert get(api, owner, p)["total"] == 1
    assert get(api, owner, p, mid, "/history")["total"] == 1
    assert get(api, owner, p, mid, "/trend")["plottable_count"] == 1
    result = api.get(f"/api/v1/reports/{rid}", headers=headers(owner)).json()["results"]
    assert result[0]["metric_name"] == "合成指标" and result[1]["standard_metric"] is None
    assert snapshot(factory, LabResult) == before and snapshot(factory, ConfirmationItem) == confirmation


def test_adapter_worker_unmatched_issue_and_review_workspace_stay_immutable(client, monkeypatch):
    api, factory = client
    auth = admin(api)
    owner = login(api, "adapter07")
    _report, path = new_report(api, owner, profile(api, owner)["id"])
    assert api.post(path + "/recognize", headers=headers(owner)).status_code == 200
    with factory() as db:
        task = claim(db, "adapter-test")
    candidate = {"metricId": "ALT", "standardName": "丙氨酸氨基转移酶"}
    rows = [{"raw": {"metric": f"合成陌生指标{index}", "result": "3.1"},
             "finalStatus": "FINAL_AUTO" if status == "AUTO_MATCHED" else "FINAL_REVIEW",
             "finalReasons": [], "metricMatch": {"status": status, "metric": candidate,
                                                   "topCandidates": [{"metric": candidate}]}}
            for index, status in enumerate(("UNMATCHED", "REVIEW", "AUTO_MATCHED"))]
    mapped = [map_row(row, task.input_manifest[0], index + 1) for index, row in enumerate(rows)]
    monkeypatch.setattr(ocr_worker, "run_pipeline", lambda *_: (
        mapped, {}, {"total_count": 3, "auto_count": 1, "review_count": 2}, "synthetic/adapter/"))
    ocr_worker.process(factory, task, "adapter-test")
    with factory() as db:
        assert db.get(OcrTask, task.id).status == "SUCCEEDED"
        persisted = list(db.scalars(select(OcrResultItem).where(OcrResultItem.ocr_task_id == task.id)
                                   .order_by(OcrResultItem.sequence_no)))
        assert [(r.standard_metric_code, r.standard_metric_name) for r in persisted] == [
            (None, None), ("ALT", candidate["standardName"]), ("ALT", candidate["standardName"])]
        assert [r.payload for r in persisted] == rows
        assert [r.evidence["metricMatch"] for r in persisted] == [r["metricMatch"] for r in rows]
    before = snapshot(factory, OcrResultItem)
    issues = api.get("/api/v1/admin/ocr-metric-issues", headers=auth).json()["items"]
    assert len(issues) == 1 and issues[0]["issue_type"] == "UNMATCHED_NAME"
    assert issues[0]["representative_name"] == "合成陌生指标0"
    assert issues[0]["occurrence_count"] == issues[0]["ingestion_count"] == 1
    items = workspace(api, owner, path)["items"]
    assert [i["review_status"] for i in items] == ["PENDING", "PENDING", "RESOLVED"]
    assert [i["standard_metric_id"] for i in items] == [None, metric_id(factory, "ALT"), metric_id(factory, "ALT")]
    alias(api, auth, metric_id(factory, "ALT"), "合成陌生指标0")
    assert api.get("/api/v1/admin/ocr-metric-issues", headers=auth).json()["items"] == []
    assert workspace(api, owner, path)["items"] == items
    assert snapshot(factory, OcrResultItem) == before


def test_ocr_issues_latest_success_privacy_dynamic_coverage_and_task_readonly(client):
    api, factory = client
    auth = admin(api)
    owner = login(api, "issues07")
    report, _ = new_report(api, owner, profile(api, owner)["id"])
    task_id = old_ocr(factory, report["id"], decisions=("FINAL_REVIEW",) * 3, codes=[None, "GLOB", "AST"])
    with factory() as db:
        first = db.get(OcrTask, task_id)
        first.pipeline_version = "frozen-test-version"
        first.result_summary = {"total_count": 3, "auto_count": 0, "review_count": 3, "private": "do not expose"}
        rows = list(db.scalars(select(OcrResultItem).where(OcrResultItem.ocr_task_id == task_id).order_by(OcrResultItem.sequence_no)))
        rows[1].standard_metric_name = "球蛋白"
        second = OcrTask(ingestion_id=report["id"], run_no=2, status="SUCCEEDED", input_manifest=[], result_summary={})
        db.add(second)
        db.flush()
        for row in rows:
            values = {c.name: getattr(row, c.name) for c in OcrResultItem.__table__.columns if c.name != "id"}
            values["ocr_task_id"] = second.id
            db.add(OcrResultItem(**values))
        db.add(OcrTask(ingestion_id=report["id"], run_no=3, status="FAILED", input_manifest=[]))
        db.commit()
    change(api, auth, "standard-metrics", metric_id(factory, "AST"), status="INACTIVE")
    before = snapshot(factory, OcrResultItem)
    response = api.get("/api/v1/admin/ocr-metric-issues", headers=auth)
    rows = response.json()["items"]
    assert {r["issue_type"] for r in rows} == {"UNMATCHED_NAME", "PRODUCT_METRIC_MISSING", "PRODUCT_METRIC_INACTIVE"}
    assert all(r["occurrence_count"] == 1 and r["ingestion_count"] == 1 for r in rows)
    assert all(s not in response.text for s in ("result_text", "payload", "raw_reference", "raw_result", "display_name", "cos_object_key"))
    alias(api, auth, metric_id(factory, "ALT"), "原名称0")
    create(api, auth, code="GLOB", name="球蛋白")
    change(api, auth, "standard-metrics", metric_id(factory, "AST"), status="ACTIVE")
    assert api.get("/api/v1/admin/ocr-metric-issues", headers=auth).json()["items"] == []
    assert snapshot(factory, OcrResultItem) == before
    response = api.get("/api/v1/admin/ocr-tasks", headers=auth, params={"pipeline_version": "frozen-test-version", "status": "SUCCEEDED"})
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["result_summary"] == {"total_count": 3, "auto_count": 0, "review_count": 3}
    assert "private" not in response.text and "input_manifest" not in response.text
    assert api.patch("/api/v1/admin/ocr-tasks", headers=auth, json={"status": "SUCCEEDED"}).status_code == 405
