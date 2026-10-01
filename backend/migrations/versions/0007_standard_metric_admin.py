"""Stage 07 product metric category and aliases only; no historical backfill."""
import sqlalchemy as sa
from alembic import op

revision = "0007_standard_metric_admin"
down_revision = "0006_metric_trend"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("standard_metrics", sa.Column("category", sa.String(80), nullable=True))
    op.create_table(
        "metric_aliases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("standard_metric_id", sa.String(36),
                  sa.ForeignKey("standard_metrics.id"), nullable=False),
        sa.Column("alias", sa.String(256), nullable=False),
        sa.Column("normalized_alias", sa.String(256), nullable=False),
        sa.Column("alias_type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="ck_metric_aliases_status"),
        sa.CheckConstraint("alias_type IN ('SYNONYM', 'ABBREVIATION', 'OCR_VARIANT', 'HOSPITAL_NAME')",
                           name="ck_metric_aliases_type"),
    )
    for field in ("standard_metric_id", "status", "normalized_alias"):
        op.create_index("ix_metric_aliases_" + field, "metric_aliases", [field])
    op.create_index("uq_metric_aliases_active_normalized", "metric_aliases", ["normalized_alias"],
                    unique=True, postgresql_where=sa.text("status = 'ACTIVE'"),
                    sqlite_where=sa.text("status = 'ACTIVE'"))


def downgrade():
    op.drop_table("metric_aliases")
    op.drop_column("standard_metrics", "category")
