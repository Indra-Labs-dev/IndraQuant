"""Phase 3 tables: backtest runs, paper trading sessions and trades
(docs/09 addendum Phase 3).

Revision ID: 002
Revises: 001
Create Date: 2026-07-21
"""

import sqlalchemy as sa
from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "backtest_runs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "instrument_id",
            sa.BigInteger(),
            sa.ForeignKey("instruments.id"),
            nullable=False,
        ),
        sa.Column("timeframe", sa.String(10), nullable=False),
        sa.Column("strategy_json", sa.Text(), nullable=False),
        sa.Column("initial_capital", sa.Numeric(24, 8), nullable=False),
        sa.Column("final_equity", sa.Numeric(24, 8), nullable=False),
        sa.Column("total_return", sa.Numeric(12, 6), nullable=False),
        sa.Column("max_drawdown", sa.Numeric(12, 6), nullable=False),
        sa.Column("trade_count", sa.Integer(), nullable=False),
        sa.Column("report_json", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_table(
        "paper_sessions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "instrument_id",
            sa.BigInteger(),
            sa.ForeignKey("instruments.id"),
            nullable=False,
        ),
        sa.Column("timeframe", sa.String(10), nullable=False),
        sa.Column("strategy_json", sa.Text(), nullable=False),
        sa.Column("initial_capital", sa.Numeric(24, 8), nullable=False),
        sa.Column("cash", sa.Numeric(24, 8), nullable=False),
        sa.Column(
            "position_qty",
            sa.Numeric(24, 8),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "status",
            sa.Enum("running", "stopped", name="paper_session_status"),
            nullable=False,
            server_default="running",
        ),
        sa.Column(
            "started_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("stopped_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "paper_trades",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.BigInteger(),
            sa.ForeignKey("paper_sessions.id"),
            nullable=False,
        ),
        sa.Column(
            "side",
            sa.Enum("buy", "sell", name="paper_trade_side"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Numeric(24, 8), nullable=False),
        sa.Column("price", sa.Numeric(24, 8), nullable=False),
        sa.Column("fee", sa.Numeric(24, 8), nullable=False),
        sa.Column(
            "executed_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("reason", sa.String(200), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("paper_trades")
    op.drop_table("paper_sessions")
    op.drop_table("backtest_runs")
