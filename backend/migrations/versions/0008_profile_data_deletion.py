"""Schedule private-file cleanup after outstanding upload credentials expire."""
import sqlalchemy as sa
from alembic import op

revision = "0008_profile_data_deletion"
down_revision = "0007_standard_metric_admin"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("file_cleanups", sa.Column("not_before", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_file_cleanups_due", "file_cleanups", ["status", "not_before", "created_at"])


def downgrade():
    op.drop_index("ix_file_cleanups_due", table_name="file_cleanups")
    op.drop_column("file_cleanups", "not_before")
