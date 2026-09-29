"""Stage 02 identity, profiles, ingestion, upload authorization and assets."""

import sqlalchemy as sa
from alembic import op

revision = "0002_profile_upload"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("wechat_openid", sa.String(128), nullable=False, unique=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("default_health_profile_id", sa.String(36)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("health_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("display_name", sa.String(80), nullable=False),
        sa.Column("relation", sa.String(16), nullable=False),
        sa.Column("gender", sa.String(16)), sa.Column("birth_date", sa.Date()),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_health_profiles_user_id", "health_profiles", ["user_id"])
    op.create_table("report_ingestions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("health_profile_id", sa.String(36), sa.ForeignKey("health_profiles.id"), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False), sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_report_ingestions_user_id", "report_ingestions", ["user_id"])
    op.create_index("ix_report_ingestions_health_profile_id", "report_ingestions", ["health_profile_id"])
    op.create_table("upload_authorizations",
        sa.Column("object_key", sa.String(256), primary_key=True),
        sa.Column("ingestion_id", sa.String(36), sa.ForeignKey("report_ingestions.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)))
    op.create_index("ix_upload_authorizations_ingestion_id", "upload_authorizations", ["ingestion_id"])
    op.create_table("report_assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ingestion_id", sa.String(36), sa.ForeignKey("report_ingestions.id"), nullable=False),
        sa.Column("cos_object_key", sa.String(256), nullable=False, unique=True),
        sa.Column("page_no", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(32), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("upload_status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("ingestion_id", "page_no"))
    op.create_index("ix_report_assets_ingestion_id", "report_assets", ["ingestion_id"])
    op.create_table("file_cleanups",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("cos_object_key", sa.String(256), nullable=False, unique=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))


def downgrade() -> None:
    for table in ("file_cleanups", "report_assets", "upload_authorizations",
                  "report_ingestions", "health_profiles", "users"):
        op.drop_table(table)
