import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.shared.infrastructure.config import settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Credentials live in .env, never in alembic.ini.
config.set_main_option("sqlalchemy.url", settings.database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all module models so autogenerate sees the full schema.
from src.modules.ai_assistant.infrastructure.sqlalchemy_repository import (  # noqa: F401,E402
    ChatMessageModel,
    MemoryFactModel,
)
from src.modules.alert_center.infrastructure.sqlalchemy_repository import AlertModel  # noqa: F401,E402
from src.modules.auth.infrastructure.sqlalchemy_repository import UserModel  # noqa: F401,E402
from src.modules.backtesting.infrastructure.sqlalchemy_repository import BacktestRunModel  # noqa: F401,E402
from src.modules.market_data.infrastructure.sqlalchemy_repository import (  # noqa: F401,E402
    ExchangeModel,
    InstrumentModel,
    OhlcvCandleModel,
)
from src.modules.model_registry.infrastructure.sqlalchemy_repository import ModelVersionModel  # noqa: F401,E402
from src.modules.paper_trading.infrastructure.sqlalchemy_repository import (  # noqa: F401,E402
    PaperSessionModel,
    PaperTradeModel,
)
from src.modules.prediction_engine.infrastructure.sqlalchemy_repository import PredictionModel  # noqa: F401,E402
from src.modules.settings.infrastructure.sqlalchemy_repository import SettingModel  # noqa: F401,E402
from src.shared.infrastructure.database import Base  # noqa: E402

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
