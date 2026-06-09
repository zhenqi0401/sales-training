"""Add user must change password flag."""

from alembic import op
import sqlalchemy as sa

revision = "b01_user_must_change_password"
down_revision = "a05_video_management_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
            comment="User must change password on first login",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "must_change_password")
