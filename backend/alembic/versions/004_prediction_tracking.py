"""Prediction tracking for self-correction (ADR-020).

Revision ID: 004
Revises: 003
Create Date: 2026-07-21
"""

import sqlalchemy as sa
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "predictions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "instrument_id",
            sa.BigInteger(),
            sa.ForeignKey("instruments.id"),
            nullable=False,
        ),
        sa.Column("timeframe", sa.String(10), nullable=False),
        sa.Column("as_of", sa.DateTime(), nullable=False),
        sa.Column("target_time", sa.DateTime(), nullable=False),
        sa.Column(
            "predicted_direction",
            sa.Enum("up", "down", name="prediction_direction"),
            nullable=False,
        ),
        sa.Column("raw_prob_up", sa.Numeric(6, 4), nullable=False),
        sa.Column("model_json", sa.Text(), nullable=False),
        sa.Column(
            "actual_direction",
            sa.Enum("up", "down", name="prediction_actual_direction"),
            nullable=True,
        ),
        sa.Column("correct", sa.Boolean(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint(
            "instrument_id", "timeframe", "as_of", name="uq_prediction_key"
        ),
    )


def downgrade() -> None:
    op.drop_table("predictions")
