"""Composition root: single place where concrete implementations are wired
(docs/04 — Dependency Injection). Routers only depend on the providers
defined here, never on concrete infrastructure directly.
"""

from collections.abc import Iterator

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from src.modules.auth.application.dto import UserProfile
from src.modules.auth.application.use_cases.get_current_user import (
    GetCurrentUserUseCase,
)
from src.modules.auth.application.use_cases.login import LoginUseCase
from src.modules.auth.infrastructure.security import (
    BcryptPasswordHasher,
    JwtTokenProvider,
)
from src.modules.auth.infrastructure.sqlalchemy_repository import (
    SqlAlchemyUserRepository,
    UserModel,
)
from src.modules.market_data.application.use_cases.get_ohlcv import GetOhlcvUseCase
from src.modules.market_data.application.use_cases.list_instruments import (
    ListInstrumentsUseCase,
)
from src.modules.market_data.infrastructure.ccxt_repository import (
    CcxtMarketDataRepository,
)
from src.modules.market_data.infrastructure.sqlalchemy_repository import (
    ExchangeModel,
    InstrumentModel,
    SqlAlchemyCandleStore,
    SqlAlchemyInstrumentRepository,
)
from src.modules.settings.application.use_cases.get_settings import GetSettingsUseCase
from src.modules.settings.application.use_cases.update_setting import (
    UpdateSettingUseCase,
)
from src.modules.settings.infrastructure.sqlalchemy_repository import (
    SqlAlchemySettingsRepository,
)
from src.shared.events.event_bus import event_bus
from src.shared.infrastructure.config import settings
from src.shared.infrastructure.database import SessionLocal
from src.shared.kernel.errors import UnauthorizedError

password_hasher = BcryptPasswordHasher()
token_provider = JwtTokenProvider(settings.jwt_secret, settings.jwt_expires_minutes)
market_data_provider = CcxtMarketDataRepository()


def get_db_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_login_use_case(
    session: Session = Depends(get_db_session),
) -> LoginUseCase:
    return LoginUseCase(
        SqlAlchemyUserRepository(session), password_hasher, token_provider
    )


def get_current_user(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_db_session),
) -> UserProfile:
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedError("missing_token", "Jeton d'authentification requis.")
    use_case = GetCurrentUserUseCase(
        SqlAlchemyUserRepository(session), token_provider
    )
    return use_case.execute(authorization.removeprefix("Bearer "))


def get_settings_use_case(
    session: Session = Depends(get_db_session),
) -> GetSettingsUseCase:
    return GetSettingsUseCase(SqlAlchemySettingsRepository(session))


def get_update_setting_use_case(
    session: Session = Depends(get_db_session),
) -> UpdateSettingUseCase:
    return UpdateSettingUseCase(SqlAlchemySettingsRepository(session))


def get_list_instruments_use_case(
    session: Session = Depends(get_db_session),
) -> ListInstrumentsUseCase:
    return ListInstrumentsUseCase(SqlAlchemyInstrumentRepository(session))


def get_ohlcv_use_case(
    session: Session = Depends(get_db_session),
) -> GetOhlcvUseCase:
    return GetOhlcvUseCase(
        SqlAlchemyInstrumentRepository(session),
        market_data_provider,
        SqlAlchemyCandleStore(session),
        event_bus,
    )


_SEED_EXCHANGE = ("binance", "Binance")
_SEED_INSTRUMENTS = (
    ("BTC/USDT", "BTC", "USDT"),
    ("ETH/USDT", "ETH", "USDT"),
    ("SOL/USDT", "SOL", "USDT"),
)
_SEED_SETTINGS = (("language", "fr"), ("theme", "dark"))


def bootstrap() -> None:
    """Idempotent single-user + referential seed (ADR-013)."""
    from sqlalchemy import select

    from src.modules.settings.infrastructure.sqlalchemy_repository import (
        SqlAlchemySettingsRepository,
        SettingModel,
    )

    session = SessionLocal()
    try:
        user = session.scalar(
            select(UserModel).where(UserModel.email == settings.admin_email)
        )
        if user is None:
            user = UserModel(
                email=settings.admin_email,
                password_hash=password_hasher.hash(settings.admin_password),
            )
            session.add(user)
            session.flush()

        exchange = session.scalar(
            select(ExchangeModel).where(ExchangeModel.ccxt_id == _SEED_EXCHANGE[0])
        )
        if exchange is None:
            exchange = ExchangeModel(
                ccxt_id=_SEED_EXCHANGE[0], display_name=_SEED_EXCHANGE[1]
            )
            session.add(exchange)
            session.flush()

        for symbol, base, quote in _SEED_INSTRUMENTS:
            exists = session.scalar(
                select(InstrumentModel).where(
                    InstrumentModel.exchange_id == exchange.id,
                    InstrumentModel.symbol == symbol,
                )
            )
            if exists is None:
                session.add(
                    InstrumentModel(
                        exchange_id=exchange.id,
                        symbol=symbol,
                        base_asset=base,
                        quote_asset=quote,
                    )
                )

        existing_keys = {
            s.setting_key
            for s in session.scalars(
                select(SettingModel).where(SettingModel.user_id == user.id)
            )
        }
        repo = SqlAlchemySettingsRepository(session)
        for key, value in _SEED_SETTINGS:
            if key not in existing_keys:
                repo.upsert(user.id, key, value)

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
