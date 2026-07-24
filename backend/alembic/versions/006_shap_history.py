"""Persist full SHAP contributions per prediction for Explainable AI
history/global importance/comparison (docs/roadmap #15).

Revision ID: 006
Revises: 005
Create Date: 2026-07-24
"""

import sqlalchemy as sa
from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("predictions", sa.Column("shap_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("predictions", "shap_json")
