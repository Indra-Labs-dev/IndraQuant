"""Multiple named conversations for the AI Assistant (sidebar UI, ChatGPT-style):
today `ai_chat_messages` is one continuous thread per user with no way to
start a fresh, separately-titled conversation. Existing history is not
discarded — each user's current messages are grouped into one conversation
so nothing is lost.

Revision ID: 003
Revises: 002
Create Date: 2026-07-30
"""

import sqlalchemy as sa
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_conversations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_conversations_user_id", "ai_conversations", ["user_id"])

    op.add_column(
        "ai_chat_messages", sa.Column("conversation_id", sa.Integer(), nullable=True)
    )

    # Data migration: one conversation per user already holding messages,
    # titled from their first message, so the existing single-thread
    # history keeps working instead of becoming orphaned.
    bind = op.get_bind()
    conversations = sa.table(
        "ai_conversations",
        sa.column("id", sa.Integer),
        sa.column("user_id", sa.BigInteger),
        sa.column("title", sa.String),
    )
    messages = sa.table(
        "ai_chat_messages",
        sa.column("id", sa.Integer),
        sa.column("user_id", sa.BigInteger),
        sa.column("conversation_id", sa.Integer),
        sa.column("content", sa.Text),
        sa.column("role", sa.String),
    )

    user_ids = bind.execute(sa.select(messages.c.user_id).distinct()).scalars().all()
    for user_id in user_ids:
        first_message = bind.execute(
            sa.select(messages.c.content)
            .where(messages.c.user_id == user_id, messages.c.role == "user")
            .order_by(messages.c.id.asc())
            .limit(1)
        ).scalar()
        title = (first_message or "Conversation")[:120]
        conversation_id = bind.execute(
            conversations.insert()
            .values(user_id=user_id, title=title)
            .returning(conversations.c.id)
        ).scalar_one()
        bind.execute(
            messages.update()
            .where(messages.c.user_id == user_id)
            .values(conversation_id=conversation_id)
        )

    op.alter_column("ai_chat_messages", "conversation_id", nullable=False)
    op.create_foreign_key(
        "fk_ai_chat_messages_conversation_id",
        "ai_chat_messages",
        "ai_conversations",
        ["conversation_id"],
        ["id"],
    )
    op.create_index(
        "ix_ai_chat_messages_conversation_id", "ai_chat_messages", ["conversation_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_ai_chat_messages_conversation_id", table_name="ai_chat_messages")
    op.drop_constraint(
        "fk_ai_chat_messages_conversation_id", "ai_chat_messages", type_="foreignkey"
    )
    op.drop_column("ai_chat_messages", "conversation_id")
    op.drop_index("ix_ai_conversations_user_id", table_name="ai_conversations")
    op.drop_table("ai_conversations")
