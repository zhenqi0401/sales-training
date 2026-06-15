"""Add practice session, message, and long-term memory tables."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "d01_add_practice_tables"
down_revision = "c01_role_unify_sales_tables"
branch_labels = None
depends_on = None


def _table_exists(name: str) -> bool:
    """Check if a table already exists in the database."""
    conn = op.get_bind()
    insp = sa.inspect(conn)
    return name in insp.get_table_names()


def upgrade() -> None:
    # ── practice_sessions ──────────────────────────────────────────
    if not _table_exists("practice_sessions"):
        op.create_table(
            "practice_sessions",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True, comment="学员ID"),
            sa.Column("module_code", sa.String(64), nullable=False, server_default="general", comment="演练场景编码"),
            sa.Column("title", sa.String(256), nullable=False, server_default="话术演练", comment="会话标题"),
            sa.Column("status", sa.String(32), nullable=False, server_default="active", comment="状态: active/completed/abandoned"),
            sa.Column("total_turns", sa.Integer(), nullable=False, server_default="0", comment="总对话轮数"),
            sa.Column("average_score", sa.Float(), nullable=True, comment="平均评分"),
            sa.Column("summary", sa.Text(), nullable=True, comment="会话总结"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="创建时间"),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="更新时间"),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )

    # ── practice_messages ──────────────────────────────────────────
    if not _table_exists("practice_messages"):
        op.create_table(
            "practice_messages",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("session_id", sa.Integer(), sa.ForeignKey("practice_sessions.id", ondelete="CASCADE"), nullable=False, index=True, comment="所属会话ID"),
            sa.Column("role", sa.String(32), nullable=False, comment="角色: user/assistant/tool"),
            sa.Column("content", sa.Text(), nullable=True, comment="消息文本内容"),
            sa.Column("tool_calls", mysql.JSON(), nullable=True, comment="工具调用记录 (MCP)"),
            sa.Column("tool_results", mysql.JSON(), nullable=True, comment="工具返回结果"),
            sa.Column("evaluation", mysql.JSON(), nullable=True, comment="AI 对用户回复的评估"),
            sa.Column("turn_number", sa.Integer(), nullable=False, server_default="0", comment="对话轮次序号"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="创建时间"),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="更新时间"),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )

    # ── long_term_memories ─────────────────────────────────────────
    if not _table_exists("long_term_memories"):
        op.create_table(
            "long_term_memories",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True, comment="学员ID"),
            sa.Column("memory_key", sa.String(256), nullable=False, comment="记忆唯一键 (用于去重合并)"),
            sa.Column("memory_value", sa.Text(), nullable=False, comment="记忆内容"),
            sa.Column("importance", sa.Integer(), nullable=False, server_default="5", comment="重要性 1-10"),
            sa.Column("source_session_id", sa.Integer(), sa.ForeignKey("practice_sessions.id", ondelete="SET NULL"), nullable=True, comment="来源会话ID"),
            sa.Column("memory_type", sa.String(64), nullable=False, server_default="insight", comment="记忆类型: insight/weakness/strength/preference/pattern"),
            sa.Column("recall_count", sa.Integer(), nullable=False, server_default="0", comment="被召回次数"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="创建时间"),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="更新时间"),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )

        # Index
        op.create_index("ix_ltm_user_memory_key", "long_term_memories", ["user_id", "memory_key"], unique=True)


def downgrade() -> None:
    if _table_exists("long_term_memories"):
        try:
            op.drop_index("ix_ltm_user_memory_key", table_name="long_term_memories")
        except Exception:
            pass
        op.drop_table("long_term_memories")
    if _table_exists("practice_messages"):
        op.drop_table("practice_messages")
    if _table_exists("practice_sessions"):
        op.drop_table("practice_sessions")
