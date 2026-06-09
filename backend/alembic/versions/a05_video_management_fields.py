"""Add video management metadata fields."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "a05_video_management_fields"
down_revision = "510b2da09aa8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("videos")}
    if "tags" not in existing_columns:
        op.add_column("videos", sa.Column("tags", mysql.JSON(), nullable=True, comment="Video tags"))
    if "product_ids" not in existing_columns:
        op.add_column("videos", sa.Column("product_ids", mysql.JSON(), nullable=True, comment="Related product IDs"))


def downgrade() -> None:
    op.drop_column("videos", "product_ids")
    op.drop_column("videos", "tags")
