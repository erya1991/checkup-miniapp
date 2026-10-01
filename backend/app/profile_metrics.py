"""Read formal results only. Callers own favorite transactions."""
from fastapi import HTTPException
from sqlalchemy import case, delete, func, literal, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.api.v1.business import profile_for
from app.models import LabReport, LabResult, MetricFavorite, StandardMetric
from app.models.entities import now, uid

# Identical safe trimming in SQL grouping and response display; no unit conversion.
UNIT_WHITESPACE = " \t\n\r\v\f\u0085\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000"


def unit_for(result):
    return ((result.unit_normalized or "").strip(UNIT_WHITESPACE)
            or (result.unit_original or "").strip(UNIT_WHITESPACE) or None)


def unit_expression():
    return func.coalesce(
        func.nullif(func.trim(LabResult.unit_normalized, UNIT_WHITESPACE), ""),
        func.nullif(func.trim(LabResult.unit_original, UNIT_WHITESPACE), ""))


def series_key(unit):
    return "unit:" + unit if unit is not None else "no-unit"


def plottable():
    return (LabResult.result_numeric.is_not(None),
            or_(LabResult.comparator.is_(None), LabResult.comparator.in_(("", "="))))


def conditions(user, profile_id, metric_id=None):
    clauses = [LabResult.health_profile_id == profile_id,
               LabResult.standard_metric_id.is_not(None),
               LabReport.user_id == user.id, LabReport.health_profile_id == profile_id]
    if metric_id is not None:
        clauses.append(LabResult.standard_metric_id == metric_id)
    return clauses


def order_latest():
    return (LabResult.examination_date.desc(),
            LabResult.examination_time.desc().nulls_last(),
            LabReport.created_at.desc(), LabReport.id.desc(),
            LabResult.sequence_no.asc(), LabResult.id.asc())


def order_trend():
    return (LabResult.examination_date.asc(),
            LabResult.examination_time.asc().nulls_first(),
            LabReport.created_at.asc(), LabReport.id.asc(),
            LabResult.sequence_no.asc(), LabResult.id.asc())


def metric_for(db, metric_id):
    metric = db.get(StandardMetric, metric_id)
    if metric is None:
        raise HTTPException(404, "STANDARD_METRIC_NOT_FOUND")
    # Status is deliberately not an existing-history filter.
    return metric


def identity(metric):
    return {"id": metric.id, "code": metric.code, "name": metric.name}


def history_item(result, report):
    return {"lab_result_id": result.id, "report_id": report.id,
            **{key: getattr(result, key) for key in (
                "metric_name", "result_text", "result_numeric", "comparator",
                "unit_original", "unit_normalized", "reference_text", "reference_low",
                "reference_high", "abnormal", "examination_date", "examination_time")},
            "unit": unit_for(result), "hospital_name": report.hospital_name,
            "report_no": report.report_no}


def cards_query(user, profile_id, metric_id=None):
    clauses = conditions(user, profile_id, metric_id)
    base = select(LabResult.id.label("result_id"), LabResult.standard_metric_id.label("metric_id"),
                  func.row_number().over(partition_by=LabResult.standard_metric_id,
                                         order_by=order_latest()).label("position"))\
        .join(LabReport, LabReport.id == LabResult.report_id).where(*clauses).subquery()
    unit_key = func.coalesce(literal("unit:") + unit_expression(), literal("no-unit"))
    stats = select(
        LabResult.standard_metric_id.label("metric_id"),
        func.count().label("history_count"),
        func.sum(case((plottable()[0] & plottable()[1], 1), else_=0)).label("point_count"),
        func.count(func.distinct(case(
            (plottable()[0] & plottable()[1], unit_key), else_=None))).label("series_count"),
    ).join(LabReport, LabReport.id == LabResult.report_id).where(*clauses)\
        .group_by(LabResult.standard_metric_id).subquery()
    return select(LabResult, LabReport, StandardMetric,
                  MetricFavorite.id.label("favorite_id"),
                  stats.c.history_count, stats.c.point_count, stats.c.series_count)\
        .join(LabReport, LabReport.id == LabResult.report_id)\
        .join(base, base.c.result_id == LabResult.id)\
        .join(StandardMetric, StandardMetric.id == base.c.metric_id)\
        .join(stats, stats.c.metric_id == base.c.metric_id)\
        .outerjoin(MetricFavorite, (MetricFavorite.health_profile_id == profile_id)
                   & (MetricFavorite.standard_metric_id == base.c.metric_id))\
        .where(base.c.position == 1)


def card(row):
    result, report, metric, favorite_id, history_count, point_count, series_count = row
    return {"standard_metric": identity(metric), "is_favorite": favorite_id is not None,
            "latest": history_item(result, report), "history_count": history_count,
            "trend_plottable_count": point_count, "trend_series_count": series_count}


def list_metrics(db, user, profile_id, page=1, page_size=20):
    profile_for(db, user, profile_id)
    query = cards_query(user, profile_id)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.execute(query.order_by(
        MetricFavorite.id.is_not(None).desc(), LabResult.examination_date.desc(),
        LabResult.examination_time.desc().nulls_last(), StandardMetric.name.asc(),
        StandardMetric.code.asc(), StandardMetric.id.asc())
        .offset((page - 1) * page_size).limit(page_size))
    return {"items": [card(row) for row in rows], "page": page, "page_size": page_size,
            "total": total, "has_more": page * page_size < total}


def detail(db, user, profile_id, metric_id):
    profile_for(db, user, profile_id)
    metric_for(db, metric_id)
    row = db.execute(cards_query(user, profile_id, metric_id)).first()
    if row is None:
        raise HTTPException(404, "PROFILE_METRIC_NOT_FOUND")
    return card(row)


def history(db, user, profile_id, metric_id, page=1, page_size=50):
    info = detail(db, user, profile_id, metric_id)
    rows = db.execute(select(LabResult, LabReport)
                      .join(LabReport, LabReport.id == LabResult.report_id)
                      .where(*conditions(user, profile_id, metric_id)).order_by(*order_latest())
                      .offset((page - 1) * page_size).limit(page_size))
    return {"items": [history_item(result, report) for result, report in rows],
            "page": page, "page_size": page_size, "total": info["history_count"],
            "has_more": page * page_size < info["history_count"]}


def trend(db, user, profile_id, metric_id):
    info = detail(db, user, profile_id, metric_id)
    query = select(
        LabResult, LabReport,
        func.row_number().over(order_by=order_latest()).label("recency"),
    ).join(LabReport, LabReport.id == LabResult.report_id)\
        .where(*conditions(user, profile_id, metric_id), *plottable())
    series, recency = {}, {}
    for result, report, position in db.execute(query.order_by(*order_trend())):
        unit = unit_for(result)
        key = series_key(unit)
        if key not in series:
            series[key] = {"series_key": key, "unit": unit, "points": []}
            recency[key] = position
        recency[key] = min(recency[key], position)
        series[key]["points"].append({
            "lab_result_id": result.id, "report_id": report.id,
            "examination_date": result.examination_date,
            "examination_time": result.examination_time, "value": result.result_numeric,
            "result_text": result.result_text, "unit": unit,
            "reference_text": result.reference_text, "abnormal": result.abnormal})
    return {"standard_metric": info["standard_metric"], "history_count": info["history_count"],
            "plottable_count": sum(len(s["points"]) for s in series.values()),
            "series": [series[key] for key in sorted(series, key=recency.get)]}


def set_favorite(db, user, profile_id, metric_id, enabled):
    profile_for(db, user, profile_id)
    metric_for(db, metric_id)
    if enabled:
        # Database UNIQUE + ON CONFLICT handles simultaneous/repeated PUTs.
        insert = pg_insert if db.get_bind().dialect.name == "postgresql" else sqlite_insert
        db.execute(insert(MetricFavorite).values(
            id=uid(), health_profile_id=profile_id, standard_metric_id=metric_id, created_at=now())
            .on_conflict_do_nothing(index_elements=["health_profile_id", "standard_metric_id"]))
    else:
        db.execute(delete(MetricFavorite).where(
            MetricFavorite.health_profile_id == profile_id,
            MetricFavorite.standard_metric_id == metric_id))
    return {"is_favorite": enabled}
