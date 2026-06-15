"""One-off fix: drop & recreate practice tables with correct schema."""
import asyncio
from app.core.database import engine
from sqlalchemy import text


async def fix():
    async with engine.begin() as conn:
        # Drop existing tables (order matters due to FK constraints)
        await conn.execute(text("DROP TABLE IF EXISTS long_term_memories"))
        await conn.execute(text("DROP TABLE IF EXISTS practice_messages"))
        await conn.execute(text("DROP TABLE IF EXISTS practice_sessions"))
        print("dropped old tables")

        # Recreate with proper schema (id PK + AUTO_INCREMENT)
        await conn.execute(text("""
            CREATE TABLE practice_sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL COMMENT '学员ID',
                module_code VARCHAR(64) NOT NULL DEFAULT 'general' COMMENT '演练场景编码',
                title VARCHAR(256) NOT NULL DEFAULT '话术演练' COMMENT '会话标题',
                status VARCHAR(32) NOT NULL DEFAULT 'active' COMMENT '状态',
                total_turns INT NOT NULL DEFAULT 0 COMMENT '总对话轮数',
                average_score FLOAT NULL COMMENT '平均评分',
                summary TEXT NULL COMMENT '会话总结',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '更新时间',
                INDEX ix_ps_user_id (user_id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """))
        print("created practice_sessions")

        await conn.execute(text("""
            CREATE TABLE practice_messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                session_id INT NOT NULL COMMENT '所属会话ID',
                role VARCHAR(32) NOT NULL COMMENT '角色',
                content TEXT NULL COMMENT '消息文本内容',
                tool_calls JSON NULL COMMENT '工具调用记录 (MCP)',
                tool_results JSON NULL COMMENT '工具返回结果',
                evaluation JSON NULL COMMENT 'AI 对用户回复的评估',
                turn_number INT NOT NULL DEFAULT 0 COMMENT '对话轮次序号',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '更新时间',
                INDEX ix_pm_session_id (session_id),
                FOREIGN KEY (session_id) REFERENCES practice_sessions(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """))
        print("created practice_messages")

        await conn.execute(text("""
            CREATE TABLE long_term_memories (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL COMMENT '学员ID',
                memory_key VARCHAR(256) NOT NULL COMMENT '记忆唯一键',
                memory_value TEXT NOT NULL COMMENT '记忆内容',
                importance INT NOT NULL DEFAULT 5 COMMENT '重要性 1-10',
                source_session_id INT NULL COMMENT '来源会话ID',
                memory_type VARCHAR(64) NOT NULL DEFAULT 'insight' COMMENT '记忆类型',
                recall_count INT NOT NULL DEFAULT 0 COMMENT '被召回次数',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '更新时间',
                UNIQUE INDEX ix_ltm_user_memory_key (user_id, memory_key),
                INDEX ix_ltm_user_id (user_id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (source_session_id) REFERENCES practice_sessions(id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """))
        print("created long_term_memories")

        print("done — all tables recreated with correct schema")


asyncio.run(fix())
