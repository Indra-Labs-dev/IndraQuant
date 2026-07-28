"""Initial schema, PostgreSQL-native (squashes the former MariaDB-era
revisions 001-007 into a single migration — local-first, mono-utilisateur,
aucune donnee de production a preserver, ADR-001/ADR-002).

Revision ID: 001
Revises:
Create Date: 2026-07-28
"""

import sqlalchemy as sa
from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None

# Native Postgres ENUM types created by the tables below - tracked here so
# downgrade() can drop them explicitly. On Postgres, op.drop_table() alone
# does NOT drop the associated CREATE TYPE ... AS ENUM, unlike MySQL where
# the enum was just inline column syntax with nothing to orphan.
_ENUMS = [
    sa.Enum("crypto", "equity", "forex", name="asset_class"),
    sa.Enum(
        "price_above", "price_below", "rsi_above", "rsi_below",
        name="alert_condition_type",
    ),
    sa.Enum("running", "stopped", name="paper_session_status"),
    sa.Enum("up", "down", name="prediction_direction"),
    sa.Enum("up", "down", name="prediction_actual_direction"),
    sa.Enum("buy", "sell", name="paper_trade_side"),
]


def upgrade() -> None:
    op.create_table(
        "exchanges",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ccxt_id", sa.String(length=50), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ccxt_id"),
    )
    op.create_table(
        "settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("setting_key", sa.String(length=100), nullable=False),
        sa.Column("setting_value", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "setting_key"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "instruments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("exchange_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=30), nullable=False),
        sa.Column("base_asset", sa.String(length=15), nullable=False),
        sa.Column("quote_asset", sa.String(length=15), nullable=False),
        sa.Column(
            "asset_class",
            sa.Enum("crypto", "equity", "forex", name="asset_class"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["exchange_id"], ["exchanges.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("exchange_id", "symbol"),
    )
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("instrument_id", sa.Integer(), nullable=False),
        sa.Column("timeframe", sa.String(length=10), nullable=False),
        sa.Column(
            "condition_type",
            sa.Enum(
                "price_above", "price_below", "rsi_above", "rsi_below",
                name="alert_condition_type",
            ),
            nullable=False,
        ),
        sa.Column("threshold", sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("message", sa.String(length=300), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("triggered_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "backtest_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("instrument_id", sa.Integer(), nullable=False),
        sa.Column("timeframe", sa.String(length=10), nullable=False),
        sa.Column("strategy_json", sa.Text(), nullable=False),
        sa.Column("initial_capital", sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column("final_equity", sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column("total_return", sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column("max_drawdown", sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column("trade_count", sa.Integer(), nullable=False),
        sa.Column("report_json", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "model_versions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("instrument_id", sa.Integer(), nullable=False),
        sa.Column("timeframe", sa.String(length=10), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("as_of", sa.DateTime(), nullable=False),
        sa.Column("champion_model_type", sa.String(length=30), nullable=False),
        sa.Column("xgboost_accuracy", sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column(
            "logistic_regression_accuracy",
            sa.Numeric(precision=6, scale=4),
            nullable=False,
        ),
        sa.Column("ensemble_accuracy", sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column("baseline_accuracy", sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column("training_rows", sa.Integer(), nullable=False),
        sa.Column("is_champion", sa.Boolean(), nullable=False),
        sa.Column("rolled_back", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("instrument_id", "timeframe", "version", name="uq_model_version"),
    )
    op.create_table(
        "ohlcv_candles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("instrument_id", sa.Integer(), nullable=False),
        sa.Column("timeframe", sa.String(length=10), nullable=False),
        sa.Column("open_time", sa.DateTime(), nullable=False),
        sa.Column("open", sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column("high", sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column("low", sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column("close", sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column("volume", sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column(
            "ingested_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("instrument_id", "timeframe", "open_time"),
    )
    op.create_table(
        "paper_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("instrument_id", sa.Integer(), nullable=False),
        sa.Column("timeframe", sa.String(length=10), nullable=False),
        sa.Column("strategy_json", sa.Text(), nullable=False),
        sa.Column("initial_capital", sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column("cash", sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column("position_qty", sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column(
            "status",
            sa.Enum("running", "stopped", name="paper_session_status"),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("stopped_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("instrument_id", sa.Integer(), nullable=False),
        sa.Column("timeframe", sa.String(length=10), nullable=False),
        sa.Column("as_of", sa.DateTime(), nullable=False),
        sa.Column("target_time", sa.DateTime(), nullable=False),
        sa.Column(
            "predicted_direction",
            sa.Enum("up", "down", name="prediction_direction"),
            nullable=False,
        ),
        sa.Column("raw_prob_up", sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column("model_json", sa.Text(), nullable=False),
        sa.Column(
            "actual_direction",
            sa.Enum("up", "down", name="prediction_actual_direction"),
            nullable=True,
        ),
        sa.Column("correct", sa.Boolean(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("predicted_expected_return", sa.Numeric(precision=12, scale=8), nullable=True),
        sa.Column("predicted_low_return", sa.Numeric(precision=12, scale=8), nullable=True),
        sa.Column("predicted_high_return", sa.Numeric(precision=12, scale=8), nullable=True),
        sa.Column("actual_return", sa.Numeric(precision=12, scale=8), nullable=True),
        sa.Column("price_in_interval", sa.Boolean(), nullable=True),
        sa.Column("shap_json", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("instrument_id", "timeframe", "as_of"),
    )
    op.create_table(
        "paper_trades",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column(
            "side", sa.Enum("buy", "sell", name="paper_trade_side"), nullable=False
        ),
        sa.Column("quantity", sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column("price", sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column("fee", sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column(
            "executed_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("reason", sa.String(length=200), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["paper_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("paper_trades")
    op.drop_table("predictions")
    op.drop_table("paper_sessions")
    op.drop_table("ohlcv_candles")
    op.drop_table("model_versions")
    op.drop_table("backtest_runs")
    op.drop_table("alerts")
    op.drop_table("instruments")
    op.drop_table("users")
    op.drop_table("settings")
    op.drop_table("exchanges")

    bind = op.get_bind()
    for enum_type in _ENUMS:
        enum_type.drop(bind, checkfirst=True)
