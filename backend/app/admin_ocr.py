"""Read only, bounded response projections of OCR identity coverage."""
from sqlalchemy import func, select

from app.metric_identity import active_dictionary, normalize_name, resolve_exact
from app.models import OcrResultItem, OcrTask, StandardMetric


def metric_issues(db, issue_type=None, page=1, page_size=20):
    latest = select(OcrTask.ingestion_id, func.max(OcrTask.run_no).label("run_no"))\
        .where(OcrTask.status == "SUCCEEDED").group_by(OcrTask.ingestion_id).subquery()
    # Only names and technical counts enter this layer; no result/reference/payload is loaded.
    query = select(OcrResultItem.raw_metric, OcrResultItem.standard_metric_code,
                   OcrResultItem.standard_metric_name, OcrTask.ingestion_id,
                   OcrResultItem.created_at).join(OcrTask, OcrTask.id == OcrResultItem.ocr_task_id)\
        .join(latest, (latest.c.ingestion_id == OcrTask.ingestion_id)
              & (latest.c.run_no == OcrTask.run_no)).where(OcrTask.status == "SUCCEEDED")\
        .order_by(OcrResultItem.created_at.desc(), OcrResultItem.id)
    metrics = {m.code: m for m in db.scalars(select(StandardMetric))}
    dictionary = active_dictionary(db)
    groups = {}
    for raw, code, canonical, ingestion_id, seen in db.execute(query):
        if code is None:
            key = normalize_name(raw)
            if not key or resolve_exact(dictionary, None, raw)[0] is not None:
                continue
            kind = "UNMATCHED_NAME"
            item = {"representative_name": raw, "normalized_name": key, "sample_names": []}
        else:
            metric = metrics.get(code)
            if metric and metric.status == "ACTIVE":
                continue
            kind = "PRODUCT_METRIC_INACTIVE" if metric else "PRODUCT_METRIC_MISSING"
            key = code
            item = {"ocr_code": code, "ocr_standard_name": canonical,
                    "standard_metric_id": metric.id if metric else None}
        group = groups.setdefault((kind, key), {**item, "issue_type": kind,
                                                "occurrence_count": 0, "ingestions": set(),
                                                "latest_seen_at": seen})
        group["occurrence_count"] += 1
        group["ingestions"].add(ingestion_id)
        if kind == "UNMATCHED_NAME" and raw not in group["sample_names"] and len(group["sample_names"]) < 3:
            group["sample_names"].append(raw)
    items = []
    for group in groups.values():
        if issue_type and group["issue_type"] != issue_type:
            continue
        group["ingestion_count"] = len(group.pop("ingestions"))
        items.append(group)
    items.sort(key=lambda g: (-g["occurrence_count"], g["issue_type"],
                              g.get("normalized_name", g.get("ocr_code", ""))))
    total = len(items)
    return {"items": items[(page - 1) * page_size:page * page_size], "total": total,
            "page": page, "page_size": page_size, "has_more": page * page_size < total}


def tasks(db, status=None, pipeline_version=None, page=1, page_size=20):
    query = select(OcrTask)
    if status:
        query = query.where(OcrTask.status == status)
    if pipeline_version:
        query = query.where(OcrTask.pipeline_version == pipeline_version)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = []
    for task in db.scalars(query.order_by(OcrTask.created_at.desc(), OcrTask.id)
                          .offset((page - 1) * page_size).limit(page_size)):
        summary = task.result_summary if isinstance(task.result_summary, dict) else {}
        counts = {key: summary[key] for key in ("total_count", "auto_count", "review_count")
                  if type(summary.get(key)) is int and summary[key] >= 0}
        items.append({**{key: getattr(task, key) for key in
                         ("id", "ingestion_id", "run_no", "status", "pipeline_version", "attempt_count",
                          "created_at", "started_at", "finished_at", "last_error_code")},
                      "result_summary": counts})
    return {"items": items, "total": total, "page": page, "page_size": page_size,
            "has_more": page * page_size < total}
