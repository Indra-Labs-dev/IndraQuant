"""Phase 6: alerts table (docs/09 addendum Phase 6).

Revision ID: 003
Revises: 002
Create Date: 2026-07-21
"""

import sqlalchemy as sa
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alerts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "instrument_id",
            sa.BigInteger(),
            sa.ForeignKey("instruments.id"),
            nullable=False,
        ),
        sa.Column("timeframe", sa.String(10), nullable=False),
        sa.Column(
            "condition_type",
            sa.Enum(
                "price_above",
                "price_below",
                "rsi_above",
                "rsi_below",
                name="alert_condition_type",
            ),
            nullable=False,
        ),
        sa.Column("threshold", sa.Numeric(24, 8), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")
        ),
        sa.Column("message", sa.String(300), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("triggered_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("alerts")
