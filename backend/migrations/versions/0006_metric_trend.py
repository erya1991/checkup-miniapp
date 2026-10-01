"""Stage 06 profile metric preferences and formal-result query index."""
import sqlalchemy as sa
from alembic import op

revision = "0006_metric_trend"
down_revision = "0005_report_management"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "metric_favorites",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("health_profile_id", sa.String(36),
                  sa.ForeignKey("health_profiles.id"), nullable=False),
        sa.Column("standard_metric_id", sa.String(36),
                  sa.ForeignKey("standard_metrics.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("health_profile_id", "standard_metric_id",
                            name="uq_metric_favorites_profile_metric"),
    )
    op.create_index("ix_lab_results_profile_metric_date", "lab_results",
                    ["health_profile_id", "standard_metric_id", "examination_date"])


def downgrade():
    op.drop_index("ix_lab_results_profile_metric_date", table_name="lab_results")
    op.drop_table("metric_favorites")
