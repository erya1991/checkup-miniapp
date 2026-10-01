"""Synthetic formal result aggregation, API security and lifecycle acceptance."""
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.exc import IntegrityError
from test_stage02 import asset, headers, ingestion, login, profile
from test_stage04 import add, new_report, old_ocr, report_info, workspace
from test_stage04 import client as stage04_client

from app.models import HealthProfile, LabReport, LabResult, MetricFavorite, StandardMetric


@pytest.fixture
def client(monkeypatch):
    yield from stage04_client.__wrapped__(monkeypatch)


def metric_id(factory, code="WBC"):
    with factory() as db:
        return db.scalar(select(StandardMetric.id).where(StandardMetric.code == code))


def saved(api, factory, owner, profile_id, entries=None, **info):
    _, path = new_report(api, owner, profile_id, manual=True)
    report_info(api, owner, path, **info)
    for entry in entries or [{"result": "5.1"}]:
        add(api, owner, path, name="合成指标", result=entry["result"],
            standard_metric_id=entry.get("metric", metric_id(factory)),
            unit_original=entry.get("unit"), reference_text=entry.get("reference", "合成参考"))
    response = api.post(path + "/commit", headers=headers(owner), json={})
    if response.status_code == 409:
        response = api.post(path + "/commit", headers=headers(owner), json={
            "duplicate_acknowledgement": response.json()["details"]["acknowledgement"]})
    assert response.status_code == 200, response.text
    rid = response.json()["report_id"]
    return rid


def get(api, owner, p, mid=None, suffix="", **params):
    path = "/api/v1/profile-metrics" + ("/" + mid + suffix if mid else "")
    response = api.get(path, headers=headers(owner), params={"health_profile_id": p, **params})
    assert response.status_code == 200, response.text
    return response.json()


def favorite(api, owner, p, mid, method="put"):
    response = getattr(api, method)(f"/api/v1/favorites/{mid}",
                                    headers=headers(owner), params={"health_profile_id": p})
    assert response.status_code == 200, response.text
    return response.json()["is_favorite"]


def test_only_formal_non_null_identity_no_dictionary_or_draft_leak(client):
    api, factory = client
    owner = login(api, "formal")
    p = profile(api, owner)["id"]
    mid = metric_id(factory)
    draft = ingestion(api, owner, p)
    asset(api, owner, draft["id"])
    old_ocr(factory, draft["id"], decisions=("FINAL_AUTO",), codes=["WBC"])
    workspace(api, owner, f"/api/v1/ingestions/{draft['id']}")
    assert get(api, owner, p)["items"] == []
    null_report = saved(api, factory, owner, p, [{"result": "9", "metric": None}])
    assert get(api, owner, p)["total"] == 0
    assert api.get(f"/api/v1/reports/{null_report}", headers=headers(owner)).json()["results"][0]["standard_metric"] is None
    saved(api, factory, owner, p, [{"result": "5", "unit": "U"}, {"result": "6", "unit": "V"}])
    rows = get(api, owner, p)
    assert rows["total"] == 1 and rows["items"][0]["standard_metric"]["id"] == mid
    assert rows["items"][0]["history_count"] == 2
    assert get(api, owner, p, mid, "/history")["total"] == 2
    first = get(api, owner, p, mid, "/history", page_size=1)
    second = get(api, owner, p, mid, "/history", page_size=1, page=2)
    assert first["has_more"] and not second["has_more"]
    assert first["total"] == second["total"] == 2
    assert first["items"][0]["lab_result_id"] != second["items"][0]["lab_result_id"]
    assert get(api, owner, p, mid, "/trend")["plottable_count"] == 2
    assert get(api, owner, p, mid)["trend_series_count"] == 2


def test_latest_medical_date_time_non_numeric_and_stable_report_order(client):
    api, factory = client
    owner = login(api, "latest")
    p = profile(api, owner)["id"]
    mid = metric_id(factory)
    ids = [saved(api, factory, owner, p, [{"result": str(i)}],
                 examination_date=d, examination_time=t)
           for i, (d, t) in enumerate([
               ("2026-07-01", "23:00"), ("2026-08-01", None),
               ("2026-08-01", "08:00"), ("2026-08-01", "14:00")])]
    # Backfilled old examination committed last must remain medically older.
    old = saved(api, factory, owner, p, [{"result": "99"}], examination_date="2026-01-01")
    ordered = get(api, owner, p, mid, "/history")["items"]
    assert [row["report_id"] for row in ordered] == [ids[3], ids[2], ids[1], ids[0], old]
    newest = saved(api, factory, owner, p, [{"result": "阴性"}], examination_date="2026-09-01")
    latest = get(api, owner, p, mid)
    assert latest["latest"]["report_id"] == newest
    assert latest["latest"]["result_text"] == "阴性" and latest["history_count"] == 6
    assert latest["trend_plottable_count"] == 5
    assert get(api, owner, p)["items"][0]["latest"]["result_text"] == "阴性"
    trend = get(api, owner, p, mid, "/trend")
    assert [point["report_id"] for point in trend["series"][0]["points"]] == [old, *ids]


def test_exact_tie_breakers_sequence_and_result_id(client):
    api, factory = client
    owner = login(api, "ties")
    p = profile(api, owner)["id"]
    mid = metric_id(factory)
    a = saved(api, factory, owner, p, [{"result": "1"}, {"result": "2"}, {"result": "3"}])
    b = saved(api, factory, owner, p, [{"result": "4"}, {"result": "5"}, {"result": "6"}])
    timestamp = datetime(2026, 8, 1, tzinfo=UTC)
    with factory() as db:
        for rid in (a, b):
            db.get(LabReport, rid).created_at = timestamp
            # Synthetic same-sequence legacy fixture to exercise final result-id tie breaker.
            for result in db.scalars(select(LabResult).where(LabResult.report_id == rid)):
                result.sequence_no = 1
        db.commit()
        expected = [(r.report_id, r.id) for r in db.scalars(
            select(LabResult).order_by(LabResult.report_id.desc(), LabResult.id.asc()))]
    history = get(api, owner, p, mid, "/history")["items"]
    assert [(r["report_id"], r["lab_result_id"]) for r in history] == expected
    assert get(api, owner, p, mid)["latest"]["lab_result_id"] == expected[0][1]
    points = get(api, owner, p, mid, "/trend")["series"][0]["points"]
    assert [(r["report_id"], r["lab_result_id"]) for r in points] == sorted(expected)


def test_same_report_repeated_metric_uses_sequence_ascending(client):
    api, factory = client
    owner = login(api, "sequence")
    p = profile(api, owner)["id"]
    saved(api, factory, owner, p, [{"result": "2"}, {"result": "1"}, {"result": "3"}])
    mid = metric_id(factory)
    assert [r["result_text"] for r in get(api, owner, p, mid, "/history")["items"]] == ["2", "1", "3"]
    assert get(api, owner, p, mid)["latest"]["result_text"] == "2"
    assert [r["result_text"] for r in get(api, owner, p, mid, "/trend")["series"][0]["points"]] == ["2", "1", "3"]


@pytest.mark.parametrize("comparator", ["<", ">", "<=", ">=", "≤", "≥", "unexpected"])
def test_comparator_not_a_precise_point(client, comparator):
    api, factory = client
    owner = login(api, "comparator")
    p = profile(api, owner)["id"]
    rid = saved(api, factory, owner, p, [{"result": comparator + "5"}])
    with factory() as db:
        row = db.scalar(select(LabResult).where(LabResult.report_id == rid))
        row.result_numeric = Decimal(5)
        row.comparator = comparator
        db.commit()
    mid = metric_id(factory)
    assert get(api, owner, p, mid)["latest"]["result_text"] == comparator + "5"
    assert get(api, owner, p, mid, "/history")["total"] == 1
    chart = get(api, owner, p, mid, "/trend")
    assert chart["series"] == [] and chart["plottable_count"] == 0


def test_units_trim_only_defaults_counts_all_allowed_comparators_and_no_parse(client):
    api, factory = client
    owner = login(api, "units")
    p = profile(api, owner)["id"]
    entries = [{"result": str(i)} for i in range(10)]
    rid = saved(api, factory, owner, p, entries)
    with factory() as db:
        rows = list(db.scalars(select(LabResult).where(LabResult.report_id == rid).order_by(LabResult.sequence_no)))
        units = [("  N  ", "O"), (None, " N "), ("", "V"), (" \t ", " V "),
                 (None, None), (None, "__NO_UNIT__"), (None, "n"),
                 ("\u3000N\u3000", None), (None, None), (None, None)]
        for i, (row, (normalized, original)) in enumerate(zip(rows, units, strict=True)):
            row.unit_normalized, row.unit_original = normalized, original
            row.comparator = [None, "", "="][i % 3]
            row.abnormal = None
            row.reference_text = f"范围{i}"
        rows[8].result_numeric = None  # Numeric-looking text is not reparsed.
        rows[9].result_numeric = None
        rows[9].result_text = "未检出"
        db.commit()
    mid = metric_id(factory)
    info = get(api, owner, p, mid)
    assert info["history_count"] == 10 and info["trend_plottable_count"] == 8
    assert info["trend_series_count"] == 5
    trend = get(api, owner, p, mid, "/trend")
    by_unit = {s["unit"]: s for s in trend["series"]}
    assert set(by_unit) == {"N", "V", None, "__NO_UNIT__", "n"}
    assert len({s["series_key"] for s in trend["series"]}) == 5
    assert len(by_unit["N"]["points"]) == 3
    assert len(by_unit["V"]["points"]) == 2
    assert all(r["abnormal"] is None for r in get(api, owner, p, mid, "/history")["items"])
    assert by_unit["N"]["points"][0]["reference_text"] == "范围0"
    assert by_unit["N"]["points"][0]["value"] == 0


def test_series_default_uses_latest_plottable_not_latest_text(client):
    api, factory = client
    owner = login(api, "default")
    p = profile(api, owner)["id"]
    saved(api, factory, owner, p, [{"result": "1", "unit": "U"}], examination_date="2026-06-01")
    saved(api, factory, owner, p, [{"result": "2", "unit": "V"}], examination_date="2026-07-01")
    saved(api, factory, owner, p, [{"result": "阴性", "unit": "U"}], examination_date="2026-08-01")
    mid = metric_id(factory)
    chart = get(api, owner, p, mid, "/trend")
    assert [s["unit"] for s in chart["series"]] == ["V", "U"]
    assert get(api, owner, p, mid)["latest"]["result_text"] == "阴性"


def test_favorite_pagination_inactive_metric_and_no_unbounded_n_plus_one(client):
    api, factory = client
    owner = login(api, "pages")
    p = profile(api, owner)["id"]
    mids = [metric_id(factory, code) for code in ("WBC", "HGB", "ALT")]
    for i, mid in enumerate(mids):
        saved(api, factory, owner, p, [{"result": "5", "metric": mid}], examination_date=f"2026-08-0{i+1}")
    assert favorite(api, owner, p, mids[0])
    assert favorite(api, owner, p, mids[0])
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(MetricFavorite)) == 1
        db.get(StandardMetric, mids[0]).status = "INACTIVE"
        db.commit()
    first = get(api, owner, p, page_size=2)
    second = get(api, owner, p, page_size=2, page=2)
    assert [c["standard_metric"]["id"] for c in first["items"] + second["items"]] == [mids[0], mids[2], mids[1]]
    assert first["total"] == 3 and first["has_more"] and not second["has_more"]
    assert get(api, owner, p, mids[0])["is_favorite"]
    assert get(api, owner, p, mids[0], "/trend")["plottable_count"] == 1
    assert not favorite(api, owner, p, mids[0], "delete")
    assert not favorite(api, owner, p, mids[0], "delete")
    queries = []
    engine = factory.kw["bind"]
    def record(conn, cursor, statement, parameters, context, many):
        queries.append(statement)
    event.listen(engine, "before_cursor_execute", record)
    try:
        get(api, owner, p)
    finally:
        event.remove(engine, "before_cursor_execute", record)
    assert len(queries) <= 4  # Auth + profile + count + one batched result query.
    history = get(api, owner, p, mids[0], "/history", page_size=1)
    assert history["total"] == 1 and not history["has_more"]


def test_same_favorite_date_time_list_name_code_id_sort(client):
    api, factory = client
    owner = login(api, "list-tie")
    p = profile(api, owner)["id"]
    mids = [metric_id(factory, code) for code in ("WBC", "HGB", "ALT")]
    for mid in mids:
        saved(api, factory, owner, p, [{"result": "3", "metric": mid}], examination_time="08:00")
    with factory() as db:
        expected = [m.id for m in db.scalars(select(StandardMetric).where(StandardMetric.id.in_(mids))
                                            .order_by(StandardMetric.name, StandardMetric.code, StandardMetric.id))]
    assert [c["standard_metric"]["id"] for c in get(api, owner, p)["items"]] == expected


def test_all_six_interfaces_owner_active_profile_errors_required_context_and_privacy(client, caplog):
    api, factory = client
    owner, stranger = login(api, "owner"), login(api, "stranger")
    p = profile(api, owner)["id"]
    mid = metric_id(factory)
    saved(api, factory, owner, p)
    routes = [("get", "/profile-metrics"), ("get", f"/profile-metrics/{mid}"),
              ("get", f"/profile-metrics/{mid}/history"), ("get", f"/profile-metrics/{mid}/trend"),
              ("put", f"/favorites/{mid}"), ("delete", f"/favorites/{mid}")]
    for method, route in routes:
        for pid in (p, str(uuid4())):
            response = getattr(api, method)("/api/v1" + route, headers=headers(stranger),
                                          params={"health_profile_id": pid})
            assert response.status_code == 404 and response.json()["code"] == "PROFILE_NOT_FOUND"
            assert response.json()["request_id"]
        assert getattr(api, method)("/api/v1" + route, headers=headers(owner)).status_code == 422
        assert getattr(api, method)("/api/v1" + route, params={"health_profile_id": p}).status_code == 401
    for route in (f"/profile-metrics/{uuid4()}", f"/favorites/{uuid4()}"):
        response = api.get("/api/v1" + route, headers=headers(owner), params={"health_profile_id": p}) if "profile-" in route else api.put("/api/v1" + route, headers=headers(owner), params={"health_profile_id": p})
        assert response.json()["code"] == "STANDARD_METRIC_NOT_FOUND"
    unused = metric_id(factory, "ALT")
    favorite(api, owner, p, unused)
    for suffix in ("", "/history", "/trend"):
        response = api.get(f"/api/v1/profile-metrics/{unused}{suffix}", headers=headers(owner),
                           params={"health_profile_id": p})
        assert response.status_code == 404 and response.json()["code"] == "PROFILE_METRIC_NOT_FOUND"
    payload = str(get(api, owner, p, mid, "/history")) + str(get(api, owner, p, mid, "/trend"))
    assert not any(term in payload for term in ("cos_object_key", "https://", "raw_result", "payload"))
    for suffix in ("", "/history"):
        for invalid in ({"page": 0}, {"page_size": 101}, {"page_size": 0}):
            response = api.get("/api/v1/profile-metrics" + (f"/{mid}{suffix}" if suffix else ""),
                               headers=headers(owner), params={"health_profile_id": p, **invalid})
            assert response.status_code == 422
    assert "合成参考" not in caplog.text and "result_text" not in caplog.text
    with factory() as db:
        db.get(HealthProfile, p).status = "DELETED"
        db.commit()
    for method, route in routes:
        assert getattr(api, method)("/api/v1" + route, headers=headers(owner),
                                   params={"health_profile_id": p}).json()["code"] == "PROFILE_NOT_FOUND"


def test_favorite_unique_constraint(client):
    api, factory = client
    owner = login(api, "unique")
    p = profile(api, owner)["id"]
    mid = metric_id(factory)
    favorite(api, owner, p, mid)
    with factory() as db:
        db.add(MetricFavorite(health_profile_id=p, standard_metric_id=mid))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_migrate_delete_favorites_dormant_restore_latest_and_other_data(client, monkeypatch):
    from app.core import cos
    monkeypatch.setattr(cos, "delete_prefix", lambda key: (_ for _ in ()).throw(RuntimeError("offline")))
    api, factory = client
    owner = login(api, "lifecycle")
    p, target = profile(api, owner)["id"], profile(api, owner, "母亲", "MOTHER")["id"]
    mid, alt = metric_id(factory), metric_id(factory, "ALT")
    old = saved(api, factory, owner, p, [{"result": "1"}], examination_date="2026-06-01")
    middle = saved(api, factory, owner, p, [{"result": "2"}], examination_date="2026-07-01")
    newest = saved(api, factory, owner, p, [{"result": "3"}], examination_date="2026-08-01")
    other = saved(api, factory, owner, p, [{"result": "9", "metric": alt}])
    favorite(api, owner, p, mid)
    response = api.post(f"/api/v1/reports/{newest}/migrate", headers=headers(owner),
                        json={"health_profile_id": target})
    assert response.status_code == 200, response.text
    assert get(api, owner, p, mid)["latest"]["report_id"] == middle
    assert get(api, owner, p, mid)["history_count"] == 2
    assert get(api, owner, target, mid)["history_count"] == 1
    assert not get(api, owner, target, mid)["is_favorite"]
    assert get(api, owner, target, mid, "/trend")["series"][0]["points"][0]["report_id"] == newest
    for rid, remaining in ((old, 1), (middle, 0)):
        assert api.delete(f"/api/v1/reports/{rid}", headers=headers(owner)).status_code == 204
        if remaining:
            assert get(api, owner, p, mid)["latest"]["report_id"] == middle
            assert get(api, owner, p, mid, "/history")["total"] == 1
            assert get(api, owner, p, mid, "/trend")["plottable_count"] == 1
    assert [c["standard_metric"]["id"] for c in get(api, owner, p)["items"]] == [alt]
    with factory() as db:
        assert db.scalar(select(MetricFavorite.id).where(MetricFavorite.health_profile_id == p))
    assert api.get(f"/api/v1/reports/{other}", headers=headers(owner)).status_code == 200
    restored = saved(api, factory, owner, p, [{"result": "4"}], examination_date="2026-09-01")
    assert get(api, owner, p, mid)["is_favorite"]
    assert get(api, owner, p, mid)["latest"]["report_id"] == restored
