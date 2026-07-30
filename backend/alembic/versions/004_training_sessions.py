"""Persisted "should be running" state for continuous training sessions
(docs/roadmap ADR-024's TrainingRunner): session state used to be in-memory
only, so a backend restart silently stopped every running session with no
way to resume — the user had to notice and manually restart each one. This
table lets the app resume them automatically on startup, the same way
paper trading sessions already do.

Revision ID: 004
Revises: 003
Create Date: 2026-07-31
"""

import sqlalchemy as sa
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "training_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("instrument_id", sa.Integer(), nullable=False),
        sa.Column("timeframe", sa.String(length=10), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("instrument_id", "timeframe"),
    )


def downgrade() -> None:
    op.drop_table("training_sessions")
