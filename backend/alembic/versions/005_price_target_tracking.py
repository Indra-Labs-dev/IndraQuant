"""Extend self-learning to price-target estimates (ADR-029).

Revision ID: 005
Revises: 004
Create Date: 2026-07-22
"""

import sqlalchemy as sa
from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "predictions",
        sa.Column("predicted_expected_return", sa.Numeric(12, 8), nullable=True),
    )
    op.add_column(
        "predictions",
        sa.Column("predicted_low_return", sa.Numeric(12, 8), nullable=True),
    )
    op.add_column(
        "predictions",
        sa.Column("predicted_high_return", sa.Numeric(12, 8), nullable=True),
    )
    op.add_column(
        "predictions", sa.Column("actual_return", sa.Numeric(12, 8), nullable=True)
    )
    op.add_column(
        "predictions", sa.Column("price_in_interval", sa.Boolean(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("predictions", "price_in_interval")
    op.drop_column("predictions", "actual_return")
    op.drop_column("predictions", "predicted_high_return")
    op.drop_column("predictions", "predicted_low_return")
    op.drop_column("predictions", "predicted_expected_return")
