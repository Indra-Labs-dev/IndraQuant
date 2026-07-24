"""Composition root: single place where concrete implementations are wired
(docs/04 — Dependency Injection). Routers only depend on the providers
defined here, never on concrete infrastructure directly.
"""

import time
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from src.modules.ai_assistant.application.use_cases.chat import ChatUseCase
from src.modules.alert_center.application.use_cases.manage_alerts import (
    CheckAlertsUseCase,
    ManageAlertsUseCase,
)
from src.modules.alert_center.infrastructure.runner import AlertRunner
from src.modules.alert_center.infrastructure.sqlalchemy_repository import (
    SqlAlchemyAlertRepository,
)
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
from src.modules.market_data.application.use_cases.get_market_status import (
    GetMarketStatusUseCase,
)
from src.modules.market_data.application.use_cases.get_ohlcv import GetOhlcvUseCase
from src.modules.market_data.application.use_cases.list_instruments import (
    ListInstrumentsUseCase,
)
from src.modules.market_data.domain.trading_calendar import equity_market_status
from src.modules.market_data.infrastructure.ccxt_repository import (
    CcxtMarketDataRepository,
)
from src.modules.market_data.infrastructure.composite_repository import (
    CompositeMarketDataRepository,
)
from src.modules.market_data.infrastructure.refresh_runner import (
    MarketDataRefreshRunner,
)
from src.modules.market_data.infrastructure.yfinance_repository import (
    YFinanceMarketDataRepository,
)
from src.modules.market_data.infrastructure.sqlalchemy_repository import (
    ExchangeModel,
    InstrumentModel,
    SqlAlchemyCandleStore,
    SqlAlchemyInstrumentRepository,
)
from src.modules.backtesting.application.use_cases.run_backtest import (
    RunBacktestUseCase,
)
from src.modules.backtesting.application.use_cases.walk_forward import (
    WalkForwardUseCase,
)
from src.modules.backtesting.infrastructure.sqlalchemy_repository import (
    SqlAlchemyBacktestRunRepository,
)
from src.modules.paper_trading.application.use_cases.manage_sessions import (
    ManageSessionsUseCase,
)
from src.modules.paper_trading.application.use_cases.process_tick import (
    ProcessTickUseCase,
)
from src.modules.portfolio_analytics.application.use_cases.get_portfolio_summary import (
    GetPortfolioSummaryUseCase,
)
from src.modules.news_intelligence.application.use_cases.analyze_news_intelligence import (
    AnalyzeNewsIntelligenceUseCase,
)
from src.modules.news_intelligence.application.use_cases.get_news import (
    GetNewsUseCase,
)
from src.modules.news_intelligence.application.use_cases.get_news_price_correlation import (
    GetNewsPriceCorrelationUseCase,
)
from src.modules.news_intelligence.infrastructure.rss_repository import (
    RssNewsRepository,
)
from src.modules.paper_trading.infrastructure.runner import PaperTradingRunner
from src.modules.sentiment_analysis.application.use_cases.analyze_news import (
    AnalyzeNewsSentimentUseCase,
)
from src.modules.sentiment_analysis.infrastructure.ollama_client import OllamaClient
from src.modules.paper_trading.infrastructure.sqlalchemy_repository import (
    SqlAlchemyPaperTradingRepository,
)
from src.modules.machine_learning.infrastructure.direction_model import DirectionModel
from src.modules.machine_learning.infrastructure.price_target_model import (
    PriceTargetModel,
)
from src.modules.economic_calendar.application.use_cases.list_events import (
    ListEventsUseCase,
)
from src.modules.meta_decision_engine.application.use_cases.get_meta_decision import (
    GetMetaDecisionUseCase,
)
from src.modules.confidence_score.application.use_cases.get_global_confidence import (
    GetGlobalConfidenceScoreUseCase,
)
from src.modules.model_registry.application.use_cases.register_model_version import (
    RegisterModelVersionUseCase,
)
from src.modules.model_registry.application.use_cases.get_model_registry import (
    GetModelRegistryUseCase,
)
from src.modules.model_registry.application.use_cases.rollback_model import (
    RollbackModelUseCase,
)
from src.modules.model_registry.application.use_cases.run_ab_test import RunAbTestUseCase
from src.modules.model_registry.infrastructure.sqlalchemy_repository import (
    SqlAlchemyModelVersionRepository,
)
from src.modules.market_regime.application.use_cases.get_market_regime import (
    GetMarketRegimeUseCase,
)
from src.modules.correlation_engine.application.use_cases.get_correlation_matrix import (
    GetCorrelationMatrixUseCase,
)
from src.modules.feature_store.application.service import FeatureStoreService
from src.modules.feature_store.application.use_cases.get_features import (
    GetFeatureVectorUseCase,
)
from src.modules.drift_detection.application.use_cases.get_drift_report import (
    GetDriftReportUseCase,
)
from src.modules.validation.application.use_cases.validate_backtest import (
    ValidateBacktestUseCase,
)
from src.modules.validation.application.use_cases.validate_model import (
    ValidatePredictionModelUseCase,
)
from src.modules.hyperparameter_optimization.application.use_cases.optimize_model import (
    OptimizeModelHyperparametersUseCase,
)
from src.modules.hyperparameter_optimization.application.use_cases.optimize_strategy import (
    OptimizeStrategyUseCase,
)
from src.modules.risk_management.application.use_cases.get_exposure_report import (
    GetExposureReportUseCase,
)
from src.modules.risk_management.application.use_cases.get_risk_budget import (
    GetRiskBudgetUseCase,
)
from src.modules.risk_management.application.use_cases.get_risk_profile import (
    GetRiskProfileUseCase,
)
from src.modules.explainable_ai.application.use_cases.compare_explanations import (
    CompareExplanationsUseCase,
)
from src.modules.explainable_ai.application.use_cases.get_feature_importance import (
    GetFeatureEvolutionUseCase,
    GetGlobalFeatureImportanceUseCase,
)
from src.modules.explainable_ai.application.use_cases.get_shap_history import (
    GetShapHistoryUseCase,
)
from src.modules.pattern_recognition.application.use_cases.detect_patterns import (
    DetectPatternsUseCase,
)
from src.modules.prediction_engine.application.use_cases.get_prediction_dashboard import (
    GetPredictionDashboardUseCase,
)
from src.modules.prediction_engine.application.use_cases.manage_training import (
    ManageTrainingUseCase,
)
from src.modules.prediction_engine.application.use_cases.predict_direction import (
    PredictDirectionUseCase,
)
from src.modules.prediction_engine.infrastructure.training_runner import TrainingRunner
from src.modules.prediction_engine.application.use_cases.resolve_predictions import (
    ResolvePredictionsUseCase,
)
from src.modules.prediction_engine.infrastructure.runner import (
    PredictionResolverRunner,
)
from src.modules.prediction_engine.infrastructure.sqlalchemy_repository import (
    SqlAlchemyPredictionRepository,
)
from src.modules.smart_money.application.use_cases.detect_smc import DetectSmcUseCase
from src.modules.settings.application.use_cases.get_settings import GetSettingsUseCase
from src.modules.settings.application.use_cases.update_setting import (
    UpdateSettingUseCase,
)
from src.modules.settings.infrastructure.sqlalchemy_repository import (
    SqlAlchemySettingsRepository,
)
from src.modules.technical_analysis.application.use_cases.compute_indicators import (
    ComputeIndicatorsUseCase,
)
from src.modules.technical_analysis.application.use_cases.get_volume_profile import (
    GetVolumeProfileUseCase,
)
from src.shared.events.event_bus import ALL_EVENT_TYPES, MarketClosed, TrainingFinished, event_bus
from src.shared.events.event_log import EventLogService
from src.shared.infrastructure.config import settings
from src.shared.infrastructure.database import SessionLocal
from src.shared.kernel.errors import UnauthorizedError

password_hasher = BcryptPasswordHasher()
token_provider = JwtTokenProvider(settings.jwt_secret, settings.jwt_expires_minutes)

event_log = EventLogService()
event_bus.subscribe_all(ALL_EVENT_TYPES, event_log.record)


def get_event_log_service() -> EventLogService:
    return event_log


market_data_provider = CompositeMarketDataRepository(
    {
        "crypto": CcxtMarketDataRepository(),
        "equity": YFinanceMarketDataRepository(),
    }
)


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


def get_market_status_use_case(
    session: Session = Depends(get_db_session),
) -> GetMarketStatusUseCase:
    return GetMarketStatusUseCase(SqlAlchemyInstrumentRepository(session))


def get_ohlcv_use_case(
    session: Session = Depends(get_db_session),
) -> GetOhlcvUseCase:
    from src.shared.infrastructure.cache import redis_client

    return GetOhlcvUseCase(
        SqlAlchemyInstrumentRepository(session),
        market_data_provider,
        SqlAlchemyCandleStore(session),
        event_bus,
        cache=redis_client,
    )


_REFRESH_TIMEFRAMES = ("1h", "1d")
_REFRESH_LOOKBACK = {"1h": timedelta(days=3), "1d": timedelta(days=30)}


def _refresh_market_data_once() -> int:
    """Proactively keeps the most-used timeframes warm in storage instead of
    only ever fetching on-demand (ADR-030). Reuses `GetOhlcvUseCase`'s
    already-tested read-through ingestion — this is purely a scheduler, the
    upsert/backfill logic itself is not duplicated here."""
    session = SessionLocal()
    refreshed = 0
    try:
        instruments = SqlAlchemyInstrumentRepository(session).list_instruments()
        ohlcv = get_ohlcv_use_case(session)
        now = datetime.now(timezone.utc)
        equity_open = equity_market_status(now).is_open

        for instrument in instruments:
            if instrument.asset_class == "equity" and not equity_open:
                event_bus.publish(MarketClosed(instrument_id=instrument.id, closed_at=now))
                continue
            for timeframe in _REFRESH_TIMEFRAMES:
                try:
                    ohlcv.execute(
                        instrument.id,
                        timeframe,
                        now - _REFRESH_LOOKBACK[timeframe],
                        now,
                        2,
                    )
                    refreshed += 1
                except Exception:
                    pass
                # Stagger calls so all instruments/timeframes don't hit the
                # upstream exchange APIs in a single burst.
                time.sleep(1)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    return refreshed


market_data_refresh_runner = MarketDataRefreshRunner(_refresh_market_data_once)


def get_compute_indicators_use_case(
    session: Session = Depends(get_db_session),
) -> ComputeIndicatorsUseCase:
    return ComputeIndicatorsUseCase(get_ohlcv_use_case(session))


def get_volume_profile_use_case(
    session: Session = Depends(get_db_session),
) -> GetVolumeProfileUseCase:
    return GetVolumeProfileUseCase(get_ohlcv_use_case(session))


def get_detect_patterns_use_case(
    session: Session = Depends(get_db_session),
) -> DetectPatternsUseCase:
    return DetectPatternsUseCase(get_ohlcv_use_case(session))


_direction_model = DirectionModel()
_price_target_model = PriceTargetModel()
_news_repository = RssNewsRepository()
_ollama_client = OllamaClient()


def get_news_use_case() -> GetNewsUseCase:
    from src.shared.infrastructure.cache import redis_client

    return GetNewsUseCase(_news_repository, cache=redis_client, event_bus=event_bus)


def get_analyze_sentiment_use_case() -> AnalyzeNewsSentimentUseCase:
    from src.shared.infrastructure.cache import redis_client

    return AnalyzeNewsSentimentUseCase(
        get_news_use_case(), _ollama_client, cache=redis_client
    )


def get_news_intelligence_use_case() -> AnalyzeNewsIntelligenceUseCase:
    from src.shared.infrastructure.cache import redis_client

    return AnalyzeNewsIntelligenceUseCase(
        get_news_use_case(), _ollama_client, cache=redis_client
    )


def get_news_price_correlation_use_case(
    session: Session = Depends(get_db_session),
) -> GetNewsPriceCorrelationUseCase:
    return GetNewsPriceCorrelationUseCase(
        get_analyze_sentiment_use_case(), get_ohlcv_use_case(session)
    )


def get_predict_direction_use_case(
    session: Session = Depends(get_db_session),
) -> PredictDirectionUseCase:
    from src.shared.infrastructure.cache import redis_client

    return PredictDirectionUseCase(
        get_ohlcv_use_case(session),
        _direction_model,
        price_target_model=_price_target_model,
        predictions=SqlAlchemyPredictionRepository(session),
        cache=redis_client,
        event_bus=event_bus,
        model_registry=RegisterModelVersionUseCase(SqlAlchemyModelVersionRepository(session)),
    )


def get_model_registry_use_case(
    session: Session = Depends(get_db_session),
) -> GetModelRegistryUseCase:
    return GetModelRegistryUseCase(SqlAlchemyModelVersionRepository(session))


def get_rollback_model_use_case(
    session: Session = Depends(get_db_session),
) -> RollbackModelUseCase:
    return RollbackModelUseCase(SqlAlchemyModelVersionRepository(session))


def get_run_ab_test_use_case(
    session: Session = Depends(get_db_session),
) -> RunAbTestUseCase:
    return RunAbTestUseCase(SqlAlchemyModelVersionRepository(session))


def _resolve_predictions_once() -> None:
    session = SessionLocal()
    try:
        ResolvePredictionsUseCase(
            SqlAlchemyPredictionRepository(session), get_ohlcv_use_case(session)
        ).execute()
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


prediction_resolver_runner = PredictionResolverRunner(_resolve_predictions_once)


def get_prediction_dashboard_use_case(
    session: Session = Depends(get_db_session),
) -> GetPredictionDashboardUseCase:
    return GetPredictionDashboardUseCase(
        SqlAlchemyPredictionRepository(session), SqlAlchemyInstrumentRepository(session)
    )


def _run_prediction_once(instrument_id: int, timeframe: str) -> None:
    session = SessionLocal()
    try:
        get_predict_direction_use_case(session).execute(instrument_id, timeframe)
        session.commit()
        event_bus.publish(
            TrainingFinished(
                instrument_id=instrument_id,
                timeframe=timeframe,
                finished_at=datetime.now(timezone.utc),
            )
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


training_runner = TrainingRunner(_run_prediction_once)


def get_manage_training_use_case(
    session: Session = Depends(get_db_session),
) -> ManageTrainingUseCase:
    return ManageTrainingUseCase(training_runner, SqlAlchemyInstrumentRepository(session))


def get_detect_smc_use_case(
    session: Session = Depends(get_db_session),
) -> DetectSmcUseCase:
    return DetectSmcUseCase(get_ohlcv_use_case(session))


def get_market_regime_use_case(
    session: Session = Depends(get_db_session),
) -> GetMarketRegimeUseCase:
    return GetMarketRegimeUseCase(get_ohlcv_use_case(session))


def get_correlation_matrix_use_case(
    session: Session = Depends(get_db_session),
) -> GetCorrelationMatrixUseCase:
    return GetCorrelationMatrixUseCase(
        get_ohlcv_use_case(session), SqlAlchemyInstrumentRepository(session)
    )


_feature_store_service: FeatureStoreService | None = None


def get_feature_store_service() -> FeatureStoreService:
    global _feature_store_service
    if _feature_store_service is None:
        from src.shared.infrastructure.cache import redis_client

        _feature_store_service = FeatureStoreService(cache=redis_client)
    return _feature_store_service


def get_feature_vector_use_case(
    session: Session = Depends(get_db_session),
) -> GetFeatureVectorUseCase:
    return GetFeatureVectorUseCase(
        get_ohlcv_use_case(session), get_feature_store_service()
    )


def get_drift_report_use_case(
    session: Session = Depends(get_db_session),
) -> GetDriftReportUseCase:
    return GetDriftReportUseCase(
        get_ohlcv_use_case(session), SqlAlchemyPredictionRepository(session)
    )


def get_validate_model_use_case(
    session: Session = Depends(get_db_session),
) -> ValidatePredictionModelUseCase:
    return ValidatePredictionModelUseCase(get_ohlcv_use_case(session))


def get_validate_backtest_use_case(
    session: Session = Depends(get_db_session),
) -> ValidateBacktestUseCase:
    return ValidateBacktestUseCase(get_ohlcv_use_case(session))


def get_optimize_strategy_use_case(
    session: Session = Depends(get_db_session),
) -> OptimizeStrategyUseCase:
    return OptimizeStrategyUseCase(get_ohlcv_use_case(session))


def get_optimize_model_use_case(
    session: Session = Depends(get_db_session),
) -> OptimizeModelHyperparametersUseCase:
    return OptimizeModelHyperparametersUseCase(get_ohlcv_use_case(session))


def get_risk_profile_use_case(
    session: Session = Depends(get_db_session),
) -> GetRiskProfileUseCase:
    return GetRiskProfileUseCase(get_ohlcv_use_case(session))


def get_shap_history_use_case(
    session: Session = Depends(get_db_session),
) -> GetShapHistoryUseCase:
    from src.shared.infrastructure.cache import redis_client

    return GetShapHistoryUseCase(SqlAlchemyPredictionRepository(session), cache=redis_client)


def get_global_feature_importance_use_case(
    session: Session = Depends(get_db_session),
) -> GetGlobalFeatureImportanceUseCase:
    from src.shared.infrastructure.cache import redis_client

    return GetGlobalFeatureImportanceUseCase(
        SqlAlchemyPredictionRepository(session), cache=redis_client
    )


def get_feature_evolution_use_case(
    session: Session = Depends(get_db_session),
) -> GetFeatureEvolutionUseCase:
    from src.shared.infrastructure.cache import redis_client

    return GetFeatureEvolutionUseCase(
        SqlAlchemyPredictionRepository(session), cache=redis_client
    )


def get_compare_explanations_use_case(
    session: Session = Depends(get_db_session),
) -> CompareExplanationsUseCase:
    from src.shared.infrastructure.cache import redis_client

    return CompareExplanationsUseCase(SqlAlchemyPredictionRepository(session), cache=redis_client)


def get_exposure_report_use_case(
    session: Session = Depends(get_db_session),
) -> GetExposureReportUseCase:
    return GetExposureReportUseCase(get_portfolio_summary_use_case(session))


def get_risk_budget_use_case(
    session: Session = Depends(get_db_session),
) -> GetRiskBudgetUseCase:
    return GetRiskBudgetUseCase(
        get_portfolio_summary_use_case(session), get_ohlcv_use_case(session)
    )


def get_meta_decision_use_case(
    session: Session = Depends(get_db_session),
) -> GetMetaDecisionUseCase:
    return GetMetaDecisionUseCase(
        get_ohlcv_use_case(session),
        get_detect_smc_use_case(session),
        get_predict_direction_use_case(session),
        get_analyze_sentiment_use_case(),
        ListEventsUseCase(),
        get_market_regime_use_case(session),
        get_feature_store_service(),
    )


def get_global_confidence_score_use_case(
    session: Session = Depends(get_db_session),
) -> GetGlobalConfidenceScoreUseCase:
    return GetGlobalConfidenceScoreUseCase(
        get_meta_decision_use_case(session),
        get_correlation_matrix_use_case(session),
        SqlAlchemyInstrumentRepository(session),
        get_ohlcv_use_case(session),
    )


def get_chat_use_case(session: Session = Depends(get_db_session)) -> ChatUseCase:
    return ChatUseCase(
        get_list_instruments_use_case(session),
        get_ohlcv_use_case(session),
        _ollama_client.chat,
    )


def get_manage_alerts_use_case(
    session: Session = Depends(get_db_session),
) -> ManageAlertsUseCase:
    return ManageAlertsUseCase(SqlAlchemyAlertRepository(session))


def _check_alerts_once() -> None:
    session = SessionLocal()
    try:
        CheckAlertsUseCase(
            SqlAlchemyAlertRepository(session), get_ohlcv_use_case(session), event_bus
        ).execute()
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


alert_runner = AlertRunner(_check_alerts_once)


def get_run_backtest_use_case(
    session: Session = Depends(get_db_session),
) -> RunBacktestUseCase:
    return RunBacktestUseCase(
        get_ohlcv_use_case(session), SqlAlchemyBacktestRunRepository(session)
    )


def get_walk_forward_use_case(
    session: Session = Depends(get_db_session),
) -> WalkForwardUseCase:
    return WalkForwardUseCase(get_ohlcv_use_case(session))


def get_backtest_repository(
    session: Session = Depends(get_db_session),
) -> SqlAlchemyBacktestRunRepository:
    return SqlAlchemyBacktestRunRepository(session)


def get_manage_sessions_use_case(
    session: Session = Depends(get_db_session),
) -> ManageSessionsUseCase:
    return ManageSessionsUseCase(
        SqlAlchemyPaperTradingRepository(session), get_ohlcv_use_case(session)
    )


def get_portfolio_summary_use_case(
    session: Session = Depends(get_db_session),
) -> GetPortfolioSummaryUseCase:
    return GetPortfolioSummaryUseCase(
        get_manage_sessions_use_case(session), SqlAlchemyInstrumentRepository(session)
    )


def _process_paper_tick(session_id: int) -> None:
    session = SessionLocal()
    try:
        ProcessTickUseCase(
            SqlAlchemyPaperTradingRepository(session), get_ohlcv_use_case(session), event_bus
        ).execute(session_id)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


paper_trading_runner = PaperTradingRunner(_process_paper_tick)


def resume_running_paper_sessions() -> None:
    session = SessionLocal()
    try:
        repository = SqlAlchemyPaperTradingRepository(session)
        for model in repository.list_sessions():
            if model.status == "running":
                paper_trading_runner.start(model.id, model.timeframe)
    finally:
        session.close()


_SEED_EXCHANGES = (
    # (ccxt_id/source_id, display_name, [(symbol, base, quote, asset_class)])
    (
        "binance",
        "Binance",
        (
            ("BTC/USDT", "BTC", "USDT", "crypto"),
            ("ETH/USDT", "ETH", "USDT", "crypto"),
            ("SOL/USDT", "SOL", "USDT", "crypto"),
            ("BNB/USDT", "BNB", "USDT", "crypto"),
            ("XRP/USDT", "XRP", "USDT", "crypto"),
            ("ADA/USDT", "ADA", "USDT", "crypto"),
            ("DOGE/USDT", "DOGE", "USDT", "crypto"),
            ("AVAX/USDT", "AVAX", "USDT", "crypto"),
            ("LINK/USDT", "LINK", "USDT", "crypto"),
            ("DOT/USDT", "DOT", "USDT", "crypto"),
            ("LTC/USDT", "LTC", "USDT", "crypto"),
            ("MATIC/USDT", "MATIC", "USDT", "crypto"),
            ("TRX/USDT", "TRX", "USDT", "crypto"),
        ),
    ),
    (
        "yfinance",
        "Yahoo Finance",
        (
            ("AAPL", "AAPL", "USD", "equity"),
            ("MSFT", "MSFT", "USD", "equity"),
            ("TSLA", "TSLA", "USD", "equity"),
            ("GOOGL", "GOOGL", "USD", "equity"),
            ("AMZN", "AMZN", "USD", "equity"),
            ("NVDA", "NVDA", "USD", "equity"),
            ("META", "META", "USD", "equity"),
            ("NFLX", "NFLX", "USD", "equity"),
            ("JPM", "JPM", "USD", "equity"),
            ("V", "V", "USD", "equity"),
            ("AMD", "AMD", "USD", "equity"),
            ("DIS", "DIS", "USD", "equity"),
        ),
    ),
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

        for source_id, display_name, instruments in _SEED_EXCHANGES:
            exchange = session.scalar(
                select(ExchangeModel).where(ExchangeModel.ccxt_id == source_id)
            )
            if exchange is None:
                exchange = ExchangeModel(ccxt_id=source_id, display_name=display_name)
                session.add(exchange)
                session.flush()

            for symbol, base, quote, asset_class in instruments:
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
                            asset_class=asset_class,
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
