"""Stage 03 OCR queue and immutable machine snapshots."""

import sqlalchemy as sa
from alembic import op

revision = "0003_ocr"
down_revision = "0002_profile_upload"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("report_ingestions", "status", type_=sa.String(32),
                    existing_type=sa.String(16), existing_nullable=False)
    op.create_table(
        "ocr_tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ingestion_id", sa.String(36), sa.ForeignKey("report_ingestions.id"), nullable=False),
        sa.Column("run_no", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("pipeline_version", sa.String(128)),
        sa.Column("input_manifest", sa.JSON(), nullable=False),
        sa.Column("report_candidates", sa.JSON()),
        sa.Column("result_summary", sa.JSON()),
        sa.Column("artifact_root", sa.String(512)),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("locked_at", sa.DateTime(timezone=True)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("worker_id", sa.String(128)),
        sa.Column("last_error_code", sa.String(64)),
        sa.Column("last_error_message", sa.String(256)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("ingestion_id", "run_no"),
    )
    op.create_index("ix_ocr_tasks_ingestion_id", "ocr_tasks", ["ingestion_id"])
    op.create_index("ix_ocr_tasks_queue", "ocr_tasks", ["status", "next_attempt_at"])
    op.create_table(
        "ocr_result_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ocr_task_id", sa.String(36), sa.ForeignKey("ocr_tasks.id"), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("source_asset_id", sa.String(36), sa.ForeignKey("report_assets.id"), nullable=False),
        sa.Column("page_no", sa.Integer(), nullable=False),
        sa.Column("bbox", sa.JSON()),
        sa.Column("raw_metric", sa.Text()),
        sa.Column("raw_result", sa.Text()),
        sa.Column("raw_unit", sa.Text()),
        sa.Column("raw_reference", sa.Text()),
        sa.Column("standard_metric_code", sa.String(64)),
        sa.Column("standard_metric_name", sa.String(256)),
        sa.Column("result_text", sa.Text()),
        sa.Column("result_numeric", sa.Numeric()),
        sa.Column("comparator", sa.String(8)),
        sa.Column("normalized_unit", sa.String(128)),
        sa.Column("reference_text", sa.Text()),
        sa.Column("reference_low", sa.Numeric()),
        sa.Column("reference_high", sa.Numeric()),
        sa.Column("abnormal", sa.String(32)),
        sa.Column("final_decision", sa.String(16), nullable=False),
        sa.Column("review_reasons", sa.JSON(), nullable=False),
        sa.Column("review_category", sa.String(32)),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("ocr_task_id", "sequence_no"),
    )
    op.create_index("ix_ocr_result_items_ocr_task_id", "ocr_result_items", ["ocr_task_id"])


def downgrade() -> None:
    op.drop_table("ocr_result_items")
    op.drop_table("ocr_tasks")
    op.alter_column("report_ingestions", "status", type_=sa.String(16),
                    existing_type=sa.String(32), existing_nullable=False)
