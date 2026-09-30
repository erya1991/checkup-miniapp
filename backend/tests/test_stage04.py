"""Synthetic Stage 04 business acceptance; PostgreSQL concurrency is separate."""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import event, func, select
from test_stage02 import asset, headers, ingestion, login, profile
from test_stage02 import client as stage02_client

from app import confirmation as service
from app.models import (
    ConfirmationItem,
    HealthProfile,
    LabReport,
    LabResult,
    OcrResultItem,
    OcrTask,
    ReportAsset,
    ReportIngestion,
    StandardMetric,
)


@pytest.fixture
def client(monkeypatch):
    for api, factory in stage02_client.__wrapped__(monkeypatch):
        with factory() as db:
            seed = json.loads((Path(__file__).parents[1] / "migrations/data/standard_metrics_v1.json")
                              .read_text(encoding="utf-8"))
            db.add_all([StandardMetric(**row) for row in seed["metrics"]])
            db.commit()
        yield api, factory


def new_report(api, owner, profile_id, manual=False):
    report = ingestion(api, owner, profile_id)
    asset(api, owner, report["id"])
    path = f"/api/v1/ingestions/{report['id']}"
    if manual:
        response = api.post(path + "/manual", headers=headers(owner))
        assert response.status_code == 200, response.text
    return report, path


def old_ocr(factory, ingestion_id, decisions=("FINAL_AUTO", "FINAL_REVIEW"), codes=None):
    with factory() as db:
        page = db.scalar(select(ReportAsset).where(ReportAsset.ingestion_id == ingestion_id))
        task = OcrTask(ingestion_id=ingestion_id, run_no=1, status="SUCCEEDED",
                       input_manifest=[{"asset_id": page.id, "page_no": page.page_no}],
                       result_summary={"total_count": len(decisions)})
        db.add(task)
        db.flush()
        for index, decision in enumerate(decisions):
            db.add(OcrResultItem(
                ocr_task_id=task.id, source_asset_id=page.id, page_no=1, sequence_no=index + 1,
                raw_metric=f"原名称{index}", raw_result="机器原始 9", raw_unit="U/L",
                raw_reference="1-4", result_text="3.1", result_numeric=Decimal("3.1"),
                comparator="=", normalized_unit="U/L", reference_text="1~4",
                reference_low=1, reference_high=4, abnormal="NORMAL",
                standard_metric_code=(codes[index] if codes else "ALT"),
                final_decision=decision, review_reasons=[] if decision == "FINAL_AUTO" else ["CHECK"],
                evidence={"synthetic": True}, payload={"synthetic": True}))
        db.get(ReportIngestion, ingestion_id).status = "PENDING_CONFIRMATION"
        db.commit()
        return task.id


def workspace(api, owner, path):
    response = api.get(path + "/confirmation", headers=headers(owner))
    assert response.status_code == 200, response.text
    return response.json()


def report_info(api, owner, path, **extra):
    response = api.patch(path + "/confirmation", headers=headers(owner),
                         json={"examination_date": "2026-08-01", "hospital_name": "合成测试医院", **extra})
    assert response.status_code == 200, response.text
    return response.json()


def patch(api, owner, path, item_id, **body):
    return api.patch(path + f"/confirmation/items/{item_id}", headers=headers(owner), json=body)


def add(api, owner, path, name="手工项", result="阴性", **extra):
    response = api.post(path + "/confirmation/items", headers=headers(owner),
                        json={"metric_name": name, "result_text": result, **extra})
    assert response.status_code == 201, response.text
    return response.json()


def machine_snapshot(factory, task_id):
    with factory() as db:
        return [{c.name: getattr(row, c.name) for c in OcrResultItem.__table__.columns}
                for row in db.scalars(select(OcrResultItem).where(OcrResultItem.ocr_task_id == task_id)
                                       .order_by(OcrResultItem.sequence_no))]


def test_old_workspace_idempotent_final_candidates_unknown_identity_and_no_formal_data(client):
    api, factory = client
    owner = login(api, "old")
    report, path = new_report(api, owner, profile(api, owner)["id"])
    task_id = old_ocr(factory, report["id"], codes=["ALT", "UNKNOWN"])
    before = machine_snapshot(factory, task_id)
    first = workspace(api, owner, path)
    second = workspace(api, owner, path)
    assert [i["id"] for i in first["items"]] == [i["id"] for i in second["items"]]
    auto, review = first["items"]
    assert auto["review_status"] == "RESOLVED" and auto["source_type"] == "OCR_AUTO"
    assert review["review_status"] == "PENDING" and first["pending_count"] == 1
    assert auto["metric_name"] == "原名称0" and auto["result_text"] == "3.1"
    assert float(auto["result_numeric"]) == 3.1 and auto["unit_normalized"] == "U/L"
    assert auto["standard_metric_id"] and review["standard_metric_id"] is None
    assert auto["source"]["asset_id"] and auto["reference_text"] == "1~4"
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(StandardMetric)) == 12
        assert db.scalar(select(func.count()).select_from(ConfirmationItem)) == 2
        assert db.scalar(select(func.count()).select_from(LabReport)) == 0
        assert db.scalar(select(func.count()).select_from(LabResult)) == 0
    assert machine_snapshot(factory, task_id) == before


@pytest.mark.parametrize("fault", ["missing_task", "failed_task", "count", "asset", "decision", "partial", "summary"])
def test_invalid_source_atomic_no_workspace(client, fault):
    api, factory = client
    owner = login(api, fault)
    report, path = new_report(api, owner, profile(api, owner)["id"])
    task_id = old_ocr(factory, report["id"])
    with factory() as db:
        task = db.get(OcrTask, task_id)
        if fault == "missing_task":
            # A later run exists without success; must not fall back to older success.
            db.add(OcrTask(ingestion_id=report["id"], run_no=2, status="FAILED", input_manifest=[]))
        elif fault == "failed_task":
            task.status = "FAILED"
        elif fault == "count":
            task.result_summary = {"total_count": 3}
        elif fault == "asset":
            task.input_manifest = []
        elif fault == "decision":
            db.scalar(select(OcrResultItem).where(OcrResultItem.ocr_task_id == task_id)).final_decision = "UNKNOWN"
        elif fault == "summary":
            task.result_summary = ["malformed"]
        else:
            row = db.scalar(select(OcrResultItem).where(OcrResultItem.ocr_task_id == task_id))
            db.delete(row)
        db.commit()
    response = api.get(path + "/confirmation", headers=headers(owner))
    assert response.json()["code"] == "CONFIRMATION_SOURCE_INVALID"
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(ConfirmationItem)) == 0
        assert db.get(ReportIngestion, report["id"]).confirmation_initialized_at is None


def test_initialization_database_failure_rolls_back_and_retries(client, monkeypatch):
    api, factory = client
    owner = login(api, "init-rollback")
    report, path = new_report(api, owner, profile(api, owner)["id"])
    task_id = old_ocr(factory, report["id"])
    before = machine_snapshot(factory, task_id)
    original = service.items_for
    calls = 0

    def fail_after_flush(db, ingestion_id):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("synthetic init failure")
        return original(db, ingestion_id)

    monkeypatch.setattr(service, "items_for", fail_after_flush)
    assert api.get(path + "/confirmation", headers=headers(owner)).status_code == 500
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(ConfirmationItem)) == 0
        assert db.get(ReportIngestion, report["id"]).confirmation_initialized_at is None
    monkeypatch.setattr(service, "items_for", original)
    assert len(workspace(api, owner, path)["items"]) == 2
    assert machine_snapshot(factory, task_id) == before


@pytest.mark.parametrize("resolution", ["ACCEPTED", "CORRECTED", "STANDARD_METRIC_SELECTED", "KEEP_ORIGINAL_NAME", "REMOVED"])
def test_review_actions_immutable_and_persistent(client, resolution):
    api, factory = client
    owner = login(api, resolution)
    report, path = new_report(api, owner, profile(api, owner)["id"])
    task_id = old_ocr(factory, report["id"], decisions=["FINAL_REVIEW"])
    before = machine_snapshot(factory, task_id)
    item = workspace(api, owner, path)["items"][0]
    body = {"resolution": resolution}
    if resolution == "CORRECTED":
        body.update(metric_name="改名", result_text="阳性", unit_original="", reference_text="复杂条件")
    elif resolution == "STANDARD_METRIC_SELECTED":
        body["standard_metric_id"] = api.get("/api/v1/standard-metrics?q=AST", headers=headers(owner)).json()[0]["id"]
    response = patch(api, owner, path, item["id"], **body)
    assert response.status_code == 200, response.text
    edited = workspace(api, owner, path)["items"][0]
    assert edited["review_status"] == "RESOLVED" and edited["resolution"] == resolution
    if resolution == "CORRECTED":
        assert edited["metric_name"] == "改名" and edited["result_numeric"] is None
        assert edited["reference_low"] is None and edited["abnormal"] is None
        assert edited["unit_normalized"] is None
    if resolution == "KEEP_ORIGINAL_NAME":
        assert edited["standard_metric_id"] is None
    assert machine_snapshot(factory, task_id) == before


def test_complete_ocr_commit_auto_edit_manual_remove_trace_and_freeze(client):
    api, factory = client
    owner = login(api, "full")
    own = profile(api, owner)
    father = profile(api, owner, "父亲", "FATHER")
    report, path = new_report(api, owner, own["id"])
    task_id = old_ocr(factory, report["id"], decisions=["FINAL_AUTO", "FINAL_AUTO", "FINAL_REVIEW", "FINAL_REVIEW"],
                       codes=["ALT", "ALT", "UNKNOWN", "ALT"])
    before = machine_snapshot(factory, task_id)
    w = workspace(api, owner, path)
    assert api.post(path + "/commit", headers=headers(owner)).json()["code"] == "INVALID_REPORT_DATE"
    report_info(api, owner, path, health_profile_id=father["id"], examination_time="09:30:00")
    pending = api.post(path + "/commit", headers=headers(owner))
    assert pending.json()["code"] == "REVIEW_PENDING" and pending.json()["details"]["pending_count"] == 2
    auto, _untouched, unknown, removed = w["items"]
    assert patch(api, owner, path, auto["id"], resolution="CORRECTED", result_text="<0.5").status_code == 200
    assert patch(api, owner, path, unknown["id"], resolution="ACCEPTED").json()["code"] == "STANDARD_METRIC_NOT_FOUND"
    assert patch(api, owner, path, unknown["id"], resolution="KEEP_ORIGINAL_NAME").status_code == 200
    assert patch(api, owner, path, removed["id"], resolution="REMOVED").status_code == 200
    manual = add(api, owner, path)["items"][-1]
    assert patch(api, owner, path, manual["id"], resolution="CORRECTED", result_text="未见异常").status_code == 200
    committed = api.post(path + "/commit", headers=headers(owner))
    assert committed.status_code == 200, committed.text
    assert committed.json()["item_count"] == 4
    assert api.post(path + "/commit", headers=headers(owner)).json() == committed.json()
    assert api.get(path + "/confirmation", headers=headers(owner)).json()["code"] == "CONFIRMATION_LOCKED"
    assert patch(api, owner, path, auto["id"], resolution="REMOVED").json()["code"] == "CONFIRMATION_LOCKED"
    assert api.post(path + "/confirmation/items", headers=headers(owner), json={
        "metric_name": "x", "result_text": "1"}).json()["code"] == "CONFIRMATION_LOCKED"
    with factory() as db:
        formal = db.get(LabReport, committed.json()["report_id"])
        assert formal.health_profile_id == father["id"] and formal.examination_date == date(2026, 8, 1)
        assert formal.examination_time.hour == 9 and formal.has_manual_items and formal.has_manual_correction
        results = db.scalars(select(LabResult).order_by(LabResult.sequence_no)).all()
        assert [r.data_source for r in results] == ["OCR_CORRECTED", "OCR_AUTO", "OCR_CORRECTED", "MANUAL"]
        assert results[0].result_numeric == Decimal("0.5") and results[0].comparator == "<"
        assert results[2].standard_metric_id is None
        assert all(r.examination_date == formal.examination_date and r.health_profile_id == father["id"] for r in results)
        assert db.get(ConfirmationItem, removed["id"]).resolution == "REMOVED"
        assert db.get(ReportIngestion, report["id"]).confirmed_at is not None
    assert machine_snapshot(factory, task_id) == before


@pytest.mark.parametrize("result,numeric,comparator", [("阴性", None, None), ("阳性", None, None),
    ("未见异常", None, None), ("3.5", Decimal("3.5"), "="), ("<0.5", Decimal("0.5"), "<"),
    ("1 至 3（复查）", None, None)])
def test_manual_results_safe_parse_and_commit(client, result, numeric, comparator):
    api, factory = client
    owner = login(api, result)
    _, path = new_report(api, owner, profile(api, owner)["id"], manual=True)
    report_info(api, owner, path)
    add(api, owner, path, result=result, reference_text="1-4")
    response = api.post(path + "/commit", headers=headers(owner))
    assert response.status_code == 200, response.text
    with factory() as db:
        item = db.scalar(select(LabResult))
        assert item.data_source == "MANUAL" and item.result_text == result
        assert item.result_numeric == numeric and item.comparator == comparator
        assert item.reference_low == 1 and item.reference_high == 4 and item.abnormal is None


def test_manual_failed_ocr_preserves_history_requires_assets_and_legal_state(client):
    api, factory = client
    owner = login(api, "manual-fallback")
    p = profile(api, owner)
    empty = ingestion(api, owner, p["id"])
    empty_path = f"/api/v1/ingestions/{empty['id']}"
    assert api.post(empty_path + "/manual", headers=headers(owner)).status_code == 409
    report, path = new_report(api, owner, p["id"])
    with factory() as db:
        db.get(ReportIngestion, report["id"]).status = "OCR_FAILED"
        task = OcrTask(ingestion_id=report["id"], run_no=1, status="FAILED", input_manifest=[], last_error_code="FAIL")
        db.add(task)
        db.commit()
        task_id = task.id
    assert api.post(path + "/manual", headers=headers(owner)).status_code == 200
    assert api.post(path + "/manual", headers=headers(owner)).status_code == 200
    assert workspace(api, owner, path)["mode"] == "MANUAL"
    report_info(api, owner, path)
    assert api.post(path + "/commit", headers=headers(owner)).json()["code"] == "NO_REPORT_ITEMS"
    add(api, owner, path, "第一项")
    add(api, owner, path, "第二项", "2")
    assert api.post(path + "/commit", headers=headers(owner)).json()["item_count"] == 2
    with factory() as db:
        assert db.get(OcrTask, task_id).last_error_code == "FAIL"
        assert db.scalar(select(func.count()).select_from(OcrResultItem)) == 0
        assert db.scalar(select(func.count()).select_from(ReportAsset)) == 1


def test_invalid_fields_dates_resolution_metric_and_empty_commit(client):
    api, factory = client
    owner = login(api, "validation")
    _, path = new_report(api, owner, profile(api, owner)["id"], manual=True)
    for invalid in ("2026-02-30", "20260801", "yesterday"):
        assert api.patch(path + "/confirmation", headers=headers(owner), json={
            "examination_date": invalid}).json()["code"] == "INVALID_REPORT_DATE"
    report_info(api, owner, path)
    item = add(api, owner, path)["items"][0]
    for body in (
        {"resolution": "CORRECTED", "result_text": " "},
        {"resolution": "CORRECTED", "metric_name": None},
        {"resolution": "ACCEPTED", "result_text": "2"},
        {"resolution": "STANDARD_METRIC_SELECTED"},
        {"resolution": "BOGUS"},
        {"resolution": "CORRECTED", "standard_metric_id": "missing"},
    ):
        assert patch(api, owner, path, item["id"], **body).status_code == 422
    assert patch(api, owner, path, "foreign-item", resolution="REMOVED").status_code == 404
    assert patch(api, owner, path, item["id"], resolution="REMOVED").status_code == 200
    assert api.post(path + "/commit", headers=headers(owner)).json()["code"] == "NO_REPORT_ITEMS"
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(LabReport)) == 0


@pytest.mark.parametrize("change", ["report", "item", "profile", "metric"])
def test_duplicates_current_fingerprint_can_save_and_never_overwrite(client, change):
    api, factory = client
    owner = login(api, "duplicate")
    p = profile(api, owner)
    father = profile(api, owner, "父亲", "FATHER")
    _, path = new_report(api, owner, p["id"], manual=True)
    report_info(api, owner, path, report_no="SYN-01")
    add(api, owner, path)
    first = api.post(path + "/commit", headers=headers(owner)).json()
    _, second_path = new_report(api, owner, p["id"], manual=True)
    report_info(api, owner, second_path, report_no="SYN-01")
    item = add(api, owner, second_path)["items"][0]
    duplicate = api.post(second_path + "/commit", headers=headers(owner))
    assert duplicate.json()["code"] == "DUPLICATE_CONFIRM_REQUIRED"
    details = duplicate.json()["details"]
    assert details["candidates"][0]["report_id"] == first["report_id"]
    if change == "report":
        report_info(api, owner, second_path, report_no="SYN-01", report_category="修改")
    elif change == "item":
        patch(api, owner, second_path, item["id"], resolution="CORRECTED", result_text="阳性")
    elif change == "metric":
        metric = api.get("/api/v1/standard-metrics?q=ALT", headers=headers(owner)).json()[0]
        patch(api, owner, second_path, item["id"], resolution="STANDARD_METRIC_SELECTED", standard_metric_id=metric["id"])
    else:
        # Switch away and back; old token must still be invalid even if final values match.
        report_info(api, owner, second_path, health_profile_id=father["id"], report_no="SYN-01")
        report_info(api, owner, second_path, health_profile_id=p["id"], report_no="SYN-01")
    retry = api.post(second_path + "/commit", headers=headers(owner), json={
        "duplicate_acknowledgement": details["acknowledgement"]})
    assert retry.json()["code"] == "DUPLICATE_CONFIRM_REQUIRED"
    saved = api.post(second_path + "/commit", headers=headers(owner), json={
        "duplicate_acknowledgement": retry.json()["details"]["acknowledgement"]})
    assert saved.status_code == 200, saved.text
    assert saved.json()["report_id"] != first["report_id"]
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(LabReport)) == 2


def test_combined_duplicate_without_report_no_and_profile_isolation(client):
    api, _ = client
    owner = login(api, "combined")
    p, other = profile(api, owner), profile(api, owner, "家人", "OTHER")
    for index, profile_id in enumerate((p["id"], p["id"], other["id"])):
        _, path = new_report(api, owner, profile_id, manual=True)
        report_info(api, owner, path)
        add(api, owner, path)
        response = api.post(path + "/commit", headers=headers(owner))
        if index == 1:
            assert response.json()["code"] == "DUPLICATE_CONFIRM_REQUIRED"
            assert response.json()["details"]["candidates"][0]["reason"] == "DATE_HOSPITAL_METRICS"
        else:
            assert response.status_code == 200, response.text


def test_commit_failure_after_partial_results_rolls_back_and_logs_no_medical_values(client, caplog):
    api, factory = client
    owner = login(api, "rollback")
    report, path = new_report(api, owner, profile(api, owner)["id"], manual=True)
    report_info(api, owner, path)
    add(api, owner, path, "synthetic-sensitive-one")
    add(api, owner, path, "synthetic-sensitive-two")
    calls = 0

    def fail_second(_mapper, _connection, _target):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("synthetic-sensitive-error")

    event.listen(LabResult, "before_insert", fail_second)
    try:
        assert api.post(path + "/commit", headers=headers(owner)).status_code == 500
    finally:
        event.remove(LabResult, "before_insert", fail_second)
    assert "synthetic-sensitive" not in caplog.text
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(LabReport)) == 0
        assert db.scalar(select(func.count()).select_from(LabResult)) == 0
        assert db.get(ReportIngestion, report["id"]).status == "PENDING_CONFIRMATION"
        assert db.get(ReportIngestion, report["id"]).confirmed_at is None
    assert api.post(path + "/commit", headers=headers(owner)).status_code == 200


def test_all_confirmation_cross_user_operations_and_profile_active_ownership(client):
    api, factory = client
    owner, foreign = login(api, "owner"), login(api, "foreign")
    own_profile, foreign_profile = profile(api, owner), profile(api, foreign)
    report, path = new_report(api, owner, own_profile["id"], manual=True)
    report_info(api, owner, path)
    item = add(api, owner, path)["items"][0]
    for method, suffix, body in (
        (api.get, "/confirmation", None),
        (api.patch, "/confirmation", {"hospital_name": "bad"}),
        (api.patch, f"/confirmation/items/{item['id']}", {"resolution": "REMOVED"}),
        (api.post, "/confirmation/items", {"metric_name": "bad", "result_text": "1"}),
        (api.post, "/commit", {}), (api.post, "/manual", {}),
    ):
        kwargs = {"json": body} if body is not None else {}
        response = method(path + suffix, headers=headers(foreign), **kwargs)
        assert response.status_code == 404 and response.json()["code"] == "REPORT_NOT_FOUND"
    assert api.patch(path + "/confirmation", headers=headers(owner), json={
        "health_profile_id": foreign_profile["id"]}).status_code == 404
    with factory() as db:
        db.get(HealthProfile, own_profile["id"]).status = "DELETED"
        db.commit()
    assert api.post(path + "/commit", headers=headers(owner)).json()["code"] == "PROFILE_NOT_FOUND"
    with factory() as db:
        assert db.get(ReportIngestion, report["id"]).status == "PENDING_CONFIRMATION"
        assert db.scalar(select(func.count()).select_from(LabReport)) == 0


def test_metric_queries_name_code_and_read_only(client):
    api, _ = client
    owner = login(api, "metric-search")
    by_code = api.get("/api/v1/standard-metrics?q=alt", headers=headers(owner)).json()
    by_name = api.get("/api/v1/standard-metrics?q=丙氨酸", headers=headers(owner)).json()
    assert by_code == by_name and by_code[0]["code"] == "ALT"
    assert api.get("/api/v1/standard-metrics?q=unknown", headers=headers(owner)).json() == []
    assert api.get("/api/v1/standard-metrics").status_code == 401
    assert api.post("/api/v1/standard-metrics", headers=headers(owner), json={}).status_code == 405


@pytest.mark.parametrize("field", ["metric_name", "result_text"])
def test_commit_revalidates_retained_fields_not_only_editor(client, field):
    api, factory = client
    owner = login(api, "commit-fields")
    _, path = new_report(api, owner, profile(api, owner)["id"], manual=True)
    report_info(api, owner, path)
    item = add(api, owner, path)["items"][0]
    with factory() as db:
        setattr(db.get(ConfirmationItem, item["id"]), field, " ")
        db.commit()
    assert api.post(path + "/commit", headers=headers(owner)).json()["code"] == "INVALID_CONFIRMATION_ITEM"
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(LabReport)) == 0


def test_commit_cannot_bypass_missing_source_items_or_convert_success_to_manual(client):
    api, factory = client
    owner = login(api, "missing-source")
    report, path = new_report(api, owner, profile(api, owner)["id"])
    old_ocr(factory, report["id"])
    w = workspace(api, owner, path)
    assert api.post(path + "/manual", headers=headers(owner)).status_code == 409
    report_info(api, owner, path)
    with factory() as db:
        db.delete(db.get(ConfirmationItem, w["items"][1]["id"]))
        db.commit()
    assert api.post(path + "/commit", headers=headers(owner)).json()["code"] == "CONFIRMATION_SOURCE_INVALID"
    with factory() as db:
        assert db.get(ReportIngestion, report["id"]).status == "PENDING_CONFIRMATION"
        assert db.scalar(select(func.count()).select_from(OcrResultItem)) == 2


def test_put_confirmation_contract_used_by_wechat_is_equivalent(client):
    api, _ = client
    owner = login(api, "wechat-put")
    _, path = new_report(api, owner, profile(api, owner)["id"], manual=True)
    response = api.put(path + "/confirmation", headers=headers(owner), json={"examination_date": "2026-08-01"})
    assert response.status_code == 200, response.text
    item = add(api, owner, path)["items"][0]
    response = api.put(path + f"/confirmation/items/{item['id']}", headers=headers(owner),
                       json={"resolution": "CORRECTED", "result_text": "阳性"})
    assert response.status_code == 200, response.text
    assert workspace(api, owner, path)["items"][0]["result_text"] == "阳性"
