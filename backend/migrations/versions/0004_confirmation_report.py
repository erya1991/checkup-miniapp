"""Stage 04 confirmation workspace and formal reports; frozen product seed v1."""

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import sqlalchemy as sa
from alembic import op

revision = "0004_confirmation_report"
down_revision = "0003_ocr"
branch_labels = None
depends_on = None


def final_columns() -> list[sa.Column]:
    return [
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("metric_name", sa.Text(), nullable=False),
        sa.Column("standard_metric_id", sa.String(36), sa.ForeignKey("standard_metrics.id")),
        sa.Column("result_text", sa.Text(), nullable=False),
        sa.Column("result_numeric", sa.Numeric()),
        sa.Column("comparator", sa.String(8)),
        sa.Column("unit_original", sa.Text()),
        sa.Column("unit_normalized", sa.String(128)),
        sa.Column("reference_text", sa.Text()),
        sa.Column("reference_low", sa.Numeric()),
        sa.Column("reference_high", sa.Numeric()),
        sa.Column("abnormal", sa.String(32)),
    ]


def upgrade() -> None:
    for column in [
        sa.Column("hospital_name", sa.String(256)),
        sa.Column("examination_date", sa.Date()),
        sa.Column("examination_time", sa.Time()),
        sa.Column("report_no", sa.String(128)),
        sa.Column("report_category", sa.String(80)),
        sa.Column("confirmation_initialized_at", sa.DateTime(timezone=True)),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
    ]:
        op.add_column("report_ingestions", column)
    metrics = op.create_table(
        "standard_metrics",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    seed = json.loads((Path(__file__).resolve().parents[1] / "data" /
                       "standard_metrics_v1.json").read_text(encoding="utf-8"))
    timestamp = datetime.now(UTC)
    op.bulk_insert(metrics, [
        {"id": str(uuid5(NAMESPACE_URL, "checkup/standard-metric/" + row["code"])),
         **row, "status": "ACTIVE", "created_at": timestamp, "updated_at": timestamp}
        for row in seed["metrics"]
    ])
    op.create_table(
        "confirmation_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ingestion_id", sa.String(36), sa.ForeignKey("report_ingestions.id"),
                  nullable=False),
        sa.Column("source_ocr_result_item_id", sa.String(36),
                  sa.ForeignKey("ocr_result_items.id"), unique=True),
        *final_columns(),
        sa.Column("source_type", sa.String(16), nullable=False),
        sa.Column("review_status", sa.String(16), nullable=False),
        sa.Column("resolution", sa.String(32)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("ingestion_id", "sequence_no"),
    )
    op.create_index("ix_confirmation_items_ingestion_id", "confirmation_items", ["ingestion_id"])
    op.create_table(
        "lab_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("health_profile_id", sa.String(36), sa.ForeignKey("health_profiles.id"),
                  nullable=False),
        sa.Column("source_ingestion_id", sa.String(36), sa.ForeignKey("report_ingestions.id"),
                  unique=True, nullable=False),
        sa.Column("hospital_name", sa.String(256)),
        sa.Column("examination_date", sa.Date(), nullable=False),
        sa.Column("examination_time", sa.Time()),
        sa.Column("report_no", sa.String(128)),
        sa.Column("report_category", sa.String(80)),
        sa.Column("has_manual_correction", sa.Boolean(), nullable=False),
        sa.Column("has_manual_items", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for field in ("user_id", "health_profile_id", "examination_date"):
        op.create_index("ix_lab_reports_" + field, "lab_reports", [field])
    op.create_table(
        "lab_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("report_id", sa.String(36), sa.ForeignKey("lab_reports.id"), nullable=False),
        sa.Column("health_profile_id", sa.String(36), sa.ForeignKey("health_profiles.id"),
                  nullable=False),
        sa.Column("source_confirmation_item_id", sa.String(36),
                  sa.ForeignKey("confirmation_items.id"), unique=True, nullable=False),
        *final_columns(),
        sa.Column("data_source", sa.String(16), nullable=False),
        sa.Column("examination_date", sa.Date(), nullable=False),
        sa.Column("examination_time", sa.Time()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for field in ("report_id", "health_profile_id", "examination_date"):
        op.create_index("ix_lab_results_" + field, "lab_results", [field])


def downgrade() -> None:
    for table in ("lab_results", "lab_reports", "confirmation_items", "standard_metrics"):
        op.drop_table(table)
    for field in ("hospital_name", "examination_date", "examination_time", "report_no",
                  "report_category", "confirmation_initialized_at", "confirmed_at"):
        op.drop_column("report_ingestions", field)
