"""Transactional Stage 07 product master-data maintenance; no medical-data writes."""
from sqlalchemy import func, or_, select

from app.confirmation import ConfirmationError
from app.metric_identity import lock_namespace, normalize_name
from app.models import ConfirmationItem, LabResult, MetricAlias, ReportIngestion, StandardMetric


def metric_for(db, metric_id, lock=False):
    query = select(StandardMetric).where(StandardMetric.id == metric_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    metric = db.scalar(query)
    if not metric:
        raise ConfirmationError("STANDARD_METRIC_NOT_FOUND", 404)
    return metric


def pending_count(db, metric_id):
    return db.scalar(select(func.count()).select_from(ConfirmationItem)
                     .join(ReportIngestion, ReportIngestion.id == ConfirmationItem.ingestion_id)
                     .where(ConfirmationItem.standard_metric_id == metric_id,
                            ReportIngestion.status == "PENDING_CONFIRMATION"))


def metric_data(db, metric):
    return {**{key: getattr(metric, key) for key in
               ("id", "code", "name", "category", "status", "created_at", "updated_at")},
            "alias_count": db.scalar(select(func.count()).select_from(MetricAlias)
                                     .where(MetricAlias.standard_metric_id == metric.id)),
            "formal_result_count": db.scalar(select(func.count()).select_from(LabResult)
                                             .where(LabResult.standard_metric_id == metric.id)),
            "pending_confirmation_count": pending_count(db, metric.id)}


def alias_data(db, alias):
    metric = metric_for(db, alias.standard_metric_id)
    return {**{key: getattr(alias, key) for key in
               ("id", "standard_metric_id", "alias", "normalized_alias", "alias_type", "status",
                "created_at", "updated_at")}, "metric_code": metric.code, "metric_name": metric.name}


def page_data(db, query, serialize, page, page_size, order):
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(query.order_by(*order).offset((page - 1) * page_size).limit(page_size))
    return {"items": [serialize(db, row) for row in rows], "total": total,
            "page": page, "page_size": page_size, "has_more": page * page_size < total}


def list_metrics(db, q, status, category, page, page_size):
    query = select(StandardMetric)
    if q.strip():
        query = query.where(or_(StandardMetric.code.icontains(q.strip(), autoescape=True),
                                StandardMetric.name.icontains(q.strip(), autoescape=True)))
    if status:
        query = query.where(StandardMetric.status == status)
    if category is not None:
        query = query.where(StandardMetric.category == category)
    return page_data(db, query, metric_data, page, page_size, [StandardMetric.code])


def list_aliases(db, q, status, metric_id, page, page_size):
    query = select(MetricAlias)
    if q.strip():
        query = query.where(or_(MetricAlias.alias.icontains(q.strip(), autoescape=True),
                                MetricAlias.normalized_alias.icontains(normalize_name(q), autoescape=True)))
    if status:
        query = query.where(MetricAlias.status == status)
    if metric_id:
        query = query.where(MetricAlias.standard_metric_id == metric_id)
    return page_data(db, query, alias_data, page, page_size,
                     [MetricAlias.normalized_alias, MetricAlias.id])


def check_metric_namespace(db, code, name):
    names = {normalize_name(code), normalize_name(name)}
    if db.scalar(select(MetricAlias.id).where(MetricAlias.status == "ACTIVE",
                                            MetricAlias.normalized_alias.in_(names)).limit(1)):
        raise ConfirmationError("METRIC_ALIAS_CONFLICT")


def clean_text(value, limit, code):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        raise ConfirmationError(code, 422)
    return value.strip()


def create_metric(db, values):
    lock_namespace(db)
    code = clean_text(values["code"], 64, "INVALID_STANDARD_METRIC").upper()
    if len(code) > 64:
        raise ConfirmationError("INVALID_STANDARD_METRIC", 422)
    name = clean_text(values["name"], 256, "INVALID_STANDARD_METRIC")
    if db.scalar(select(StandardMetric.id).where(StandardMetric.code == code)):
        raise ConfirmationError("STANDARD_METRIC_CODE_CONFLICT")
    check_metric_namespace(db, code, name)
    metric = StandardMetric(code=code, name=name, category=(values.get("category") or "").strip() or None)
    db.add(metric)
    db.flush()
    return metric


def update_metric(db, metric_id, values):
    if "code" in values:
        raise ConfirmationError("STANDARD_METRIC_CODE_IMMUTABLE", 422)
    lock_namespace(db)
    metric = metric_for(db, metric_id, lock=True)
    name = clean_text(values.get("name", metric.name), 256, "INVALID_STANDARD_METRIC")
    status = values.get("status", metric.status)
    if status not in {"ACTIVE", "INACTIVE"}:
        raise ConfirmationError("INVALID_STANDARD_METRIC", 422)
    if status == "ACTIVE":
        check_metric_namespace(db, metric.code, name)
    if status == "INACTIVE" and metric.status == "ACTIVE":
        count = pending_count(db, metric.id)
        if count:
            raise ConfirmationError("STANDARD_METRIC_IN_USE_BY_PENDING_CONFIRMATION", pending_count=count)
    metric.name, metric.status = name, status
    if "category" in values:
        metric.category = (values["category"] or "").strip() or None
    db.flush()
    return metric


def check_alias(db, normalized, target_id, alias_id=None):
    target = metric_for(db, target_id, lock=True)
    if target.status != "ACTIVE":
        raise ConfirmationError("METRIC_ALIAS_TARGET_INACTIVE")
    query = select(MetricAlias.id).where(MetricAlias.status == "ACTIVE",
                                         MetricAlias.normalized_alias == normalized)
    if alias_id:
        query = query.where(MetricAlias.id != alias_id)
    if db.scalar(query.limit(1)):
        raise ConfirmationError("METRIC_ALIAS_DUPLICATE")
    for metric in db.scalars(select(StandardMetric).where(StandardMetric.status == "ACTIVE")):
        if normalized in {normalize_name(metric.code), normalize_name(metric.name)}:
            raise ConfirmationError("METRIC_ALIAS_CONFLICT")


def save_alias(db, values, alias_id=None):
    if alias_id and "standard_metric_id" in values:
        raise ConfirmationError("METRIC_ALIAS_TARGET_IMMUTABLE", 422)
    lock_namespace(db)
    alias = db.scalar(select(MetricAlias).where(MetricAlias.id == alias_id).with_for_update()) if alias_id else None
    if alias_id and alias is None:
        raise ConfirmationError("METRIC_ALIAS_NOT_FOUND", 404)
    target_id = alias.standard_metric_id if alias else values["standard_metric_id"]
    raw = values.get("alias", alias.alias if alias else None)
    clean_text(raw, 256, "INVALID_METRIC_ALIAS")
    # Keep the exact input as the administrative fact.
    if len(raw) > 256:
        raise ConfirmationError("INVALID_METRIC_ALIAS", 422)
    normalized = normalize_name(raw)
    if not normalized or len(normalized) > 256:
        raise ConfirmationError("INVALID_METRIC_ALIAS", 422)
    status = values.get("status", alias.status if alias else "ACTIVE")
    kind = values.get("alias_type", alias.alias_type if alias else None)
    if status not in {"ACTIVE", "INACTIVE"} or kind not in {
            "SYNONYM", "ABBREVIATION", "OCR_VARIANT", "HOSPITAL_NAME"}:
        raise ConfirmationError("INVALID_METRIC_ALIAS", 422)
    if status == "ACTIVE":
        check_alias(db, normalized, target_id, alias_id)
    if alias is None:
        alias = MetricAlias(standard_metric_id=target_id)
        db.add(alias)
    alias.alias, alias.normalized_alias, alias.alias_type, alias.status = raw, normalized, kind, status
    db.flush()
    return alias
