"""Model Registry for MLOps (docs/roadmap #8): versioned history of every
model actually (re)trained by the Prediction Engine, with champion/challenger
tracking and rollback support.

Revision ID: 007
Revises: 006
Create Date: 2026-07-24
"""

import sqlalchemy as sa
from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_versions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "instrument_id",
            sa.BigInteger(),
            sa.ForeignKey("instruments.id"),
            nullable=False,
        ),
        sa.Column("timeframe", sa.String(10), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("as_of", sa.DateTime(), nullable=False),
        sa.Column("champion_model_type", sa.String(30), nullable=False),
        sa.Column("xgboost_accuracy", sa.Numeric(6, 4), nullable=False),
        sa.Column("logistic_regression_accuracy", sa.Numeric(6, 4), nullable=False),
        sa.Column("ensemble_accuracy", sa.Numeric(6, 4), nullable=False),
        sa.Column("baseline_accuracy", sa.Numeric(6, 4), nullable=False),
        sa.Column("training_rows", sa.Integer(), nullable=False),
        sa.Column("is_champion", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("rolled_back", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint(
            "instrument_id", "timeframe", "version", name="uq_model_version"
        ),
    )


def downgrade() -> None:
    op.drop_table("model_versions")
