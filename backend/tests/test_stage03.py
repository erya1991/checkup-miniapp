import io
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from test_stage02 import asset, headers, ingestion, login, profile
from test_stage02 import client as stage02_client

from app import ocr_pipeline, ocr_queue, ocr_worker
from app.models import OcrResultItem, OcrTask, ReportIngestion
from app.ocr_pipeline import OcrExecutionError, map_row
from app.ocr_queue import claim, fail


@pytest.fixture
def stage03_client(monkeypatch):
    yield from stage02_client.__wrapped__(monkeypatch)


@pytest.mark.parametrize(("lease_seconds", "heartbeat_seconds"),
                         [(60, 20), (120, 40), (1800, 60)])
def test_lease_and_heartbeat_share_configuration(monkeypatch, lease_seconds, heartbeat_seconds):
    settings = SimpleNamespace(ocr_task_lease_seconds=lease_seconds)
    monkeypatch.setattr(ocr_queue, "get_settings", lambda: settings)
    monkeypatch.setattr(ocr_worker, "get_settings", lambda: settings)
    assert ocr_queue.lease_duration() == timedelta(seconds=lease_seconds)
    assert ocr_worker.heartbeat_interval_seconds() == heartbeat_seconds


def test_ingestion_records_reopen_old_success_and_isolate_profiles(stage03_client):
    api, factory = stage03_client
    owner, outsider = login(api, "record-owner"), login(api, "record-outsider")
    first_profile = profile(api, owner)
    other_profile = profile(api, owner, "家人", "OTHER")
    foreign_profile = profile(api, outsider)
    old = ingestion(api, owner, first_profile["id"])
    for _ in range(3):
        asset(api, owner, old["id"])
    newest = ingestion(api, owner, first_profile["id"])
    own_other = ingestion(api, owner, other_profile["id"])
    foreign = ingestion(api, outsider, foreign_profile["id"])
    with factory() as db:
        old_row = db.get(ReportIngestion, old["id"])
        old_row.created_at = datetime(2026, 1, 1, tzinfo=UTC)
        old_row.status = "PENDING_CONFIRMATION"
        db.add(OcrTask(ingestion_id=old["id"], run_no=1, status="SUCCEEDED",
                       input_manifest=[], result_summary={"total_count": 59,
                                                          "auto_count": 57,
                                                          "review_count": 2}))
        db.commit()

    path = f"/api/v1/ingestions?health_profile_id={first_profile['id']}"
    response = api.get(path, headers=headers(owner))
    assert response.status_code == 200
    rows = response.json()
    assert [row["id"] for row in rows] == [newest["id"], old["id"]]
    assert rows[0]["result_summary"] is None
    assert rows[1]["created_at"] and len(rows[1]["assets"]) == 3
    assert rows[1]["status"] == "PENDING_CONFIRMATION"
    assert rows[1]["result_summary"] == {
        "total_count": 59, "auto_count": 57, "review_count": 2}
    assert api.get(f"/api/v1/ingestions/{old['id']}/ocr",
                   headers=headers(owner)).json()["task"]["result_summary"] == rows[1]["result_summary"]
    assert [row["id"] for row in api.get(
        f"/api/v1/ingestions?health_profile_id={other_profile['id']}",
        headers=headers(owner)).json()] == [own_other["id"]]
    assert api.get(f"/api/v1/ingestions?health_profile_id={foreign_profile['id']}",
                   headers=headers(owner)).status_code == 404
    assert [row["id"] for row in api.get("/api/v1/ingestions",
                                        headers=headers(outsider)).json()] == [foreign["id"]]


def test_recognize_freezes_input_and_retry_preserves_runs(stage03_client):
    api, factory = stage03_client
    user = login(api, "owner")
    outsider = login(api, "outsider")
    p = profile(api, user)
    report = ingestion(api, user, p["id"])
    path = f"/api/v1/ingestions/{report['id']}"
    assert api.post(path + "/recognize", headers=headers(user)).status_code == 409
    _, page1 = asset(api, user, report["id"])
    _, page2 = asset(api, user, report["id"])
    api.put(path + "/assets/order", headers=headers(user),
            json={"asset_ids": [page2["id"], page1["id"]]})
    assert api.post(path + "/recognize", headers=headers(outsider)).status_code == 404
    first = api.post(path + "/recognize", headers=headers(user))
    assert first.status_code == 200, first.text
    first_id = first.json()["task"]["id"]
    assert first.json()["ingestion_status"] == "QUEUED"
    assert api.post(path + "/recognize", headers=headers(user)).json()["task"]["id"] == first_id
    with factory() as db:
        task = db.get(OcrTask, first_id)
        assert [(item["asset_id"], item["page_no"]) for item in task.input_manifest] == [
            (page2["id"], 1), (page1["id"], 2)]
    for method, suffix, body in (
        (api.post, "/upload-authorizations", {"mime_type": "image/jpeg"}),
        (api.post, "/assets", {"object_key": "x", "mime_type": "image/jpeg", "file_size": 1}),
        (api.put, "/assets/order", {"asset_ids": [page1["id"], page2["id"]]}),
    ):
        response = method(path + suffix, headers=headers(user), json=body)
        assert response.status_code == 409
        assert response.json()["code"] == "INGESTION_INPUT_FROZEN"
    assert api.delete(path + f"/assets/{page1['id']}", headers=headers(user)).status_code == 409
    assert api.get(path + f"/assets/{page1['id']}/preview", headers=headers(user)).status_code == 200
    assert api.get(path + "/ocr", headers=headers(outsider)).status_code == 404
    assert api.post(path + "/ocr/retry", headers=headers(outsider)).status_code == 404
    with factory() as db:
        claimed = claim(db, "worker-1")
        assert claimed.id == first_id and claimed.attempt_count == 1
        assert fail(db, first_id, "worker-1", "OCR_INPUT_INVALID")
    failed = api.get(path + "/ocr", headers=headers(user)).json()
    assert failed["ingestion_status"] == "OCR_FAILED"
    assert failed["task"]["error_code"] == "OCR_INPUT_INVALID"
    assert api.post(path + "/recognize", headers=headers(user)).status_code == 409
    second = api.post(path + "/ocr/retry", headers=headers(user)).json()
    assert second["task"]["run_no"] == 2
    assert second["task"]["id"] != first_id
    assert api.post(path + "/ocr/retry", headers=headers(user)).json()["task"]["id"] == second["task"]["id"]
    with factory() as db:
        assert len(db.scalars(select(OcrTask).where(OcrTask.ingestion_id == report["id"])).all()) == 2
        assert db.get(OcrTask, first_id).status == "FAILED"
        assert db.get(ReportIngestion, report["id"]).status == "QUEUED"


def test_pipeline_mapping_preserves_machine_decision():
    asset_manifest = {"asset_id": "asset-1", "page_no": 2}
    row = {"raw": {"metric": "原始名", "result": "3.1", "unit": "mmol/L", "reference": "1~4"},
           "resolved": {"result": "3.1", "reference": "1~4", "unit": "mmol/L"},
           "metricMatch": {"metric": {"metricId": "CODE", "standardName": "标准名"}},
           "resultValidation": {"structuredResult": {"numericValue": 3.1, "comparator": "="},
                                "structuredReference": {"low": 1, "high": 4},
                                "abnormal": {"final": "NORMAL"}},
           "effectiveUnit": {"normalizedUnit": "mmol/L"},
           "finalStatus": "FINAL_REVIEW", "finalReasons": ["UNIT_REVIEW"],
           "reviewCategory": "SAFE_REVIEW"}
    mapped = map_row(row, asset_manifest, 1)
    assert mapped["final_decision"] == "FINAL_REVIEW"
    assert mapped["review_category"] == "SAFE_REVIEW"
    assert mapped["standard_metric_code"] == "CODE"
    assert str(mapped["result_numeric"]) == "3.1"
    assert mapped["page_no"] == 2
    row["reviewCategory"] = "PIPELINE_GAP"
    assert map_row(row, asset_manifest, 2)["final_decision"] == "FINAL_REVIEW"


def test_worker_review_is_success_without_formal_report(stage03_client, monkeypatch):
    api, factory = stage03_client
    user = login(api, "worker-review")
    p = profile(api, user)
    report = ingestion(api, user, p["id"])
    _, page = asset(api, user, report["id"])
    path = f"/api/v1/ingestions/{report['id']}"
    api.post(path + "/recognize", headers=headers(user))
    with factory() as db:
        task = claim(db, "worker-test")
    mapped = map_row({"raw": {"metric": "待核对", "result": "1", "unit": "x", "reference": ""},
                      "resolved": {"result": "1", "unit": "x"},
                      "finalStatus": "FINAL_REVIEW", "finalReasons": ["SAFE_REVIEW"]},
                     {"asset_id": page["id"], "page_no": 1}, 1)
    monkeypatch.setattr(ocr_worker, "run_pipeline", lambda *_: (
        [mapped], {}, {"total_count": 1, "auto_count": 0, "review_count": 1}, "private/root/"))
    ocr_worker.process(factory, task, "worker-test")
    status = api.get(path + "/ocr", headers=headers(user)).json()
    assert status["ingestion_status"] == "PENDING_CONFIRMATION"
    assert status["task"]["status"] == "SUCCEEDED"
    assert status["task"]["result_summary"] == {
        "total_count": 1, "auto_count": 0, "review_count": 1}
    with factory() as db:
        item = db.scalar(select(OcrResultItem).where(OcrResultItem.ocr_task_id == task.id))
        assert item.final_decision == "FINAL_REVIEW"
        assert db.get(OcrTask, task.id).artifact_root == "private/root/"


def test_bounded_automatic_retry_and_deterministic_failure(stage03_client):
    api, factory = stage03_client
    user = login(api, "retry-limit")
    p = profile(api, user)
    report = ingestion(api, user, p["id"])
    asset(api, user, report["id"])
    path = f"/api/v1/ingestions/{report['id']}"
    task_id = api.post(path + "/recognize", headers=headers(user)).json()["task"]["id"]
    for attempt in range(1, 4):
        with factory() as db:
            task = claim(db, "worker")
            assert task.id == task_id and task.attempt_count == attempt
            assert fail(db, task_id, "worker", "OCR_COS_READ_FAILED", recoverable=True)
            task = db.get(OcrTask, task_id)
            if attempt < 3:
                assert task.status == "QUEUED" and task.next_attempt_at is not None
                task.next_attempt_at = None  # advance scheduled time in this isolated test
                db.commit()
            else:
                assert task.status == "FAILED"
                assert db.get(ReportIngestion, report["id"]).status == "OCR_FAILED"
    assert api.get(path + "/ocr", headers=headers(user)).json()["task"]["attempt_count"] == 3

    second_id = api.post(path + "/ocr/retry", headers=headers(user)).json()["task"]["id"]
    with factory() as db:
        second = claim(db, "worker")
        assert second.id == second_id
        assert fail(db, second_id, "worker", "OCR_OUTPUT_INVALID", recoverable=False)
        assert db.get(OcrTask, second_id).attempt_count == 1
        assert db.get(OcrTask, second_id).status == "FAILED"


def test_failed_pipeline_input_cleans_local_work(monkeypatch, tmp_path):
    class FakeCos:
        def get_object(self, **_kwargs):
            return {"Body": io.BytesIO(b"short")}

    monkeypatch.setattr(ocr_pipeline, "client", FakeCos)
    monkeypatch.setattr(ocr_pipeline, "get_settings", lambda: SimpleNamespace(
        cos_bucket="private-test", ocr_work_dir=str(tmp_path),
        ocr_normal_python="python", ocr_paddle_python="python",
        ocr_page_timeout_seconds=10))
    task = SimpleNamespace(ingestion_id="test", run_no=1, attempt_count=1,
                           input_manifest=[{"asset_id": "asset", "page_no": 1,
                                            "cos_object_key": "key", "file_size": 100}])
    with pytest.raises(OcrExecutionError, match="OCR_INPUT_SIZE_MISMATCH"):
        ocr_pipeline.run_pipeline(task, "user")
    assert not list(tmp_path.iterdir())
