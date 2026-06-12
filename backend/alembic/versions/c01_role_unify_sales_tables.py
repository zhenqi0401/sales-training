"""Unify user roles and add sales tables."""

from alembic import op
import sqlalchemy as sa

revision = "c01_role_unify_sales_tables"
down_revision = "b01_user_must_change_password"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    # 1. Migrate legacy role values
    op.execute(
        "UPDATE users SET role = 'admin' WHERE role IN ('super_admin', 'training_admin', 'instructor')"
    )

    # 2. Create sales_methodologies table
    if "sales_methodologies" not in tables:
        op.create_table(
            "sales_methodologies",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("title", sa.String(256), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("source", sa.String(64), server_default="manual"),
            sa.Column("source_audio_file_id", sa.Integer(), nullable=True),
            sa.Column("tags", sa.Text(), server_default=""),
            sa.Column("status", sa.String(32), server_default="published"),
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    # 3. Create sales_audio_files table
    if "sales_audio_files" not in tables:
        op.create_table(
            "sales_audio_files",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("file_url", sa.String(512), nullable=False),
            sa.Column("filename", sa.String(256), server_default=""),
            sa.Column("duration", sa.Integer(), server_default="0"),
            sa.Column("file_size", sa.Integer(), server_default="0"),
            sa.Column("transcript", sa.Text(), server_default=""),
            sa.Column("summary", sa.Text(), server_default=""),
            sa.Column("methodology_id", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(32), server_default="uploaded"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table("sales_audio_files")
    op.drop_table("sales_methodologies")
