"""Product identity only. Never imported by the frozen OCR matcher."""
import re
import unicodedata

from sqlalchemy import select, text

from app.models import MetricAlias, StandardMetric

# Serialize cross-table namespace checks in PostgreSQL, without another business table.
NAMESPACE_LOCK_KEY = 707001


def normalize_name(value: str | None) -> str:
    name = unicodedata.normalize("NFKC", value or "").strip().lstrip("*").strip()
    name = name.replace("Γ", "γ").replace("ɣ", "γ").casefold()
    return re.sub(r"[\s\-_.\/·()\[\]【】]+", "", name)


def lock_namespace(db):
    if db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": NAMESPACE_LOCK_KEY})


def active_dictionary(db, lock=False):
    query = select(StandardMetric).where(StandardMetric.status == "ACTIVE")\
        .order_by(StandardMetric.id)
    if lock:
        query = query.with_for_update(read=True).execution_options(populate_existing=True)
    metrics = list(db.scalars(query))
    by_code = {m.code: m.id for m in metrics}
    by_name = {}
    for metric in metrics:
        for name in (metric.name, metric.code):
            by_name.setdefault(normalize_name(name), set()).add(metric.id)
    aliases = dict(db.execute(select(MetricAlias.normalized_alias, MetricAlias.standard_metric_id)
                             .where(MetricAlias.status == "ACTIVE",
                                    MetricAlias.standard_metric_id.in_(by_code.values()))).all())
    return by_code, by_name, aliases


def resolve_exact(dictionary, ocr_code, raw_metric):
    by_code, by_name, aliases = dictionary
    if ocr_code in by_code:
        return by_code[ocr_code], True
    normalized = normalize_name(raw_metric)
    if not normalized:
        return None, False
    targets = by_name.get(normalized, set())
    if targets:
        # Existing canonical names are not unique. Ambiguous identities fail closed.
        return (next(iter(targets)) if len(targets) == 1 else None), False
    return aliases.get(normalized), False
