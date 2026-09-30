"""Stage 05 file cleanup target types."""
import sqlalchemy as sa
from alembic import op

revision = "0005_report_management"
down_revision = "0004_confirmation_report"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("file_cleanups", sa.Column("target_type", sa.String(16), nullable=False, server_default="OBJECT"))
    op.create_check_constraint("ck_file_cleanup_target_type", "file_cleanups", "target_type IN ('OBJECT', 'PREFIX')")


def downgrade():
    op.drop_constraint("ck_file_cleanup_target_type", "file_cleanups", type_="check")
    op.drop_column("file_cleanups", "target_type")
