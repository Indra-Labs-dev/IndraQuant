"""Phase 1 initial schema (docs/09-modele-donnees.md).

Revision ID: 001
Revises:
Create Date: 2026-07-21
"""

import sqlalchemy as sa
from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_table(
        "settings",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("setting_key", sa.String(100), nullable=False),
        sa.Column("setting_value", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("user_id", "setting_key"),
    )

    op.create_table(
        "exchanges",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("ccxt_id", sa.String(50), nullable=False, unique=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")
        ),
    )

    op.create_table(
        "instruments",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "exchange_id",
            sa.BigInteger(),
            sa.ForeignKey("exchanges.id"),
            nullable=False,
        ),
        sa.Column("symbol", sa.String(30), nullable=False),
        sa.Column("base_asset", sa.String(15), nullable=False),
        sa.Column("quote_asset", sa.String(15), nullable=False),
        sa.Column(
            "asset_class",
            sa.Enum("crypto", "equity", "forex", name="asset_class"),
            nullable=False,
            server_default="crypto",
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")
        ),
        sa.UniqueConstraint("exchange_id", "symbol"),
    )

    op.create_table(
        "ohlcv_candles",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "instrument_id",
            sa.BigInteger(),
            sa.ForeignKey("instruments.id"),
            nullable=False,
        ),
        sa.Column("timeframe", sa.String(10), nullable=False),
        sa.Column("open_time", sa.DateTime(), nullable=False),
        sa.Column("open", sa.Numeric(24, 8), nullable=False),
        sa.Column("high", sa.Numeric(24, 8), nullable=False),
        sa.Column("low", sa.Numeric(24, 8), nullable=False),
        sa.Column("close", sa.Numeric(24, 8), nullable=False),
        sa.Column("volume", sa.Numeric(24, 8), nullable=False),
        sa.Column(
            "ingested_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint(
            "instrument_id", "timeframe", "open_time", name="uq_candle_key"
        ),
    )


def downgrade() -> None:
    op.drop_table("ohlcv_candles")
    op.drop_table("instruments")
    op.drop_table("exchanges")
    op.drop_table("settings")
    op.drop_table("users")
