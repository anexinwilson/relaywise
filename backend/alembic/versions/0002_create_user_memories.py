"""create cross-session user memory table

Restores the durable half of the AgentCore memory strategies (semantic facts
and preferences). The per-session half is handled by LangGraph's checkpointer.
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_user_memories"
down_revision = "0001_conversations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_memories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="fact"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_session_id", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        # Repeating the same fact across chats must not create duplicate rows.
        sa.UniqueConstraint("user_id", "content", name="uq_user_memory_content"),
    )
    op.create_index("ix_user_memories_user_id", "user_memories", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_memories_user_id", table_name="user_memories")
    op.drop_table("user_memories")
