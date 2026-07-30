from datetime import datetime, timedelta, timezone

from src.modules.ai_assistant.application.tools.instrument_resolver import (
    resolve_instrument,
)
from src.shared.kernel.errors import AppError

_TIMEFRAME_SECONDS = {
    "1s": 1, "5s": 5, "30s": 30, "1m": 60, "5m": 300,
    "15m": 900, "1h": 3_600, "4h": 14_400, "1d": 86_400,
}
_ALLOWED_SETTING_KEYS = {"theme", "language", "ai_temperature", "ai_max_tokens", "ai_tools_enabled"}


def _ok(dto) -> dict:
    return {"ok": True, **dto.model_dump(mode="json")}


def _error(message: str) -> dict:
    return {"ok": False, "error": message}


def _lookback(timeframe: str, limit: int) -> tuple[datetime, datetime]:
    seconds = _TIMEFRAME_SECONDS.get(timeframe, 3_600)
    end = datetime.now(timezone.utc)
    start = end - timedelta(seconds=seconds * limit)
    return start, end


async def _run(coro_fn) -> dict:
    """Every executor's body is `await coro_fn()` wrapped the same way — the
    model must never see a raw traceback, only a {"ok": False, "error": ...}
    it can react to in French."""
    try:
        return await coro_fn()
    except AppError as error:
        return _error(error.message)
    except Exception as error:  # defensive: an unexpected bug must not crash the chat
        return _error(str(error))


# ---------------------------------------------------------------------------
# market_data / technical_analysis
# ---------------------------------------------------------------------------

async def exec_list_instruments(instruments_uc, args: dict, user_id: int) -> dict:
    async def _call():
        return _ok(await instruments_uc.execute())

    return await _run(_call)


async def exec_get_market_status(instruments_uc, market_status_uc, args: dict, user_id: int) -> dict:
    async def _call():
        instrument = await resolve_instrument(args["symbol"], instruments_uc)
        if instrument is None:
            return _error(f"instrument introuvable : {args['symbol']}")
        return _ok(await market_status_uc.execute(instrument.id))

    return await _run(_call)


async def exec_get_ohlcv(instruments_uc, ohlcv_uc, args: dict, user_id: int) -> dict:
    async def _call():
        instrument = await resolve_instrument(args["symbol"], instruments_uc)
        if instrument is None:
            return _error(f"instrument introuvable : {args['symbol']}")
        limit = int(args.get("limit", 100))
        start, end = _lookback(args["timeframe"], limit)
        return _ok(await ohlcv_uc.execute(instrument.id, args["timeframe"], start, end, limit))

    return await _run(_call)


async def exec_compute_indicators(instruments_uc, compute_indicators_uc, args: dict, user_id: int) -> dict:
    async def _call():
        instrument = await resolve_instrument(args["symbol"], instruments_uc)
        if instrument is None:
            return _error(f"instrument introuvable : {args['symbol']}")
        limit = int(args.get("limit", 200))
        start, end = _lookback(args["timeframe"], limit)
        return _ok(
            await compute_indicators_uc.execute(
                instrument.id, args["timeframe"], start, end, limit, args["indicators"]
            )
        )

    return await _run(_call)


async def exec_get_volume_profile(instruments_uc, volume_profile_uc, args: dict, user_id: int) -> dict:
    async def _call():
        instrument = await resolve_instrument(args["symbol"], instruments_uc)
        if instrument is None:
            return _error(f"instrument introuvable : {args['symbol']}")
        limit = int(args.get("limit", 200))
        start, end = _lookback(args["timeframe"], limit)
        return _ok(
            await volume_profile_uc.execute(
                instrument.id, args["timeframe"], start, end, limit, args.get("bins", 10)
            )
        )

    return await _run(_call)


async def exec_detect_patterns(instruments_uc, detect_patterns_uc, args: dict, user_id: int) -> dict:
    async def _call():
        instrument = await resolve_instrument(args["symbol"], instruments_uc)
        if instrument is None:
            return _error(f"instrument introuvable : {args['symbol']}")
        limit = int(args.get("limit", 200))
        start, end = _lookback(args["timeframe"], limit)
        return _ok(await detect_patterns_uc.execute(instrument.id, args["timeframe"], start, end, limit))

    return await _run(_call)


async def exec_detect_smc(instruments_uc, detect_smc_uc, args: dict, user_id: int) -> dict:
    async def _call():
        instrument = await resolve_instrument(args["symbol"], instruments_uc)
        if instrument is None:
            return _error(f"instrument introuvable : {args['symbol']}")
        limit = int(args.get("limit", 200))
        start, end = _lookback(args["timeframe"], limit)
        return _ok(await detect_smc_uc.execute(instrument.id, args["timeframe"], start, end, limit))

    return await _run(_call)


# ---------------------------------------------------------------------------
# prediction_engine / market_regime / correlation_engine / meta_decision /
# confidence_score
# ---------------------------------------------------------------------------

async def exec_predict_direction(instruments_uc, predict_direction_uc, args: dict, user_id: int) -> dict:
    async def _call():
        instrument = await resolve_instrument(args["symbol"], instruments_uc)
        if instrument is None:
            return _error(f"instrument introuvable : {args['symbol']}")
        return _ok(await predict_direction_uc.execute(instrument.id, args["timeframe"]))

    return await _run(_call)


async def exec_get_prediction_dashboard(instruments_uc, dashboard_uc, args: dict, user_id: int) -> dict:
    async def _call():
        instrument_id = None
        if args.get("symbol"):
            instrument = await resolve_instrument(args["symbol"], instruments_uc)
            if instrument is None:
                return _error(f"instrument introuvable : {args['symbol']}")
            instrument_id = instrument.id
        return _ok(
            await dashboard_uc.execute(args["timeframe"], instrument_id, int(args.get("limit", 50)))
        )

    return await _run(_call)


async def exec_get_market_regime(instruments_uc, market_regime_uc, args: dict, user_id: int) -> dict:
    async def _call():
        instrument = await resolve_instrument(args["symbol"], instruments_uc)
        if instrument is None:
            return _error(f"instrument introuvable : {args['symbol']}")
        return _ok(await market_regime_uc.execute(instrument.id, args["timeframe"]))

    return await _run(_call)


async def exec_get_correlation_matrix(instruments_uc, correlation_matrix_uc, args: dict, user_id: int) -> dict:
    async def _call():
        ids = []
        for symbol in args["symbols"]:
            instrument = await resolve_instrument(symbol, instruments_uc)
            if instrument is None:
                return _error(f"instrument introuvable : {symbol}")
            ids.append(instrument.id)
        return _ok(
            await correlation_matrix_uc.execute(ids, args["timeframe"], args.get("window", 20))
        )

    return await _run(_call)


async def exec_get_meta_decision(instruments_uc, meta_decision_uc, args: dict, user_id: int) -> dict:
    async def _call():
        instrument = await resolve_instrument(args["symbol"], instruments_uc)
        if instrument is None:
            return _error(f"instrument introuvable : {args['symbol']}")
        return _ok(await meta_decision_uc.execute(instrument.id, args["timeframe"]))

    return await _run(_call)


async def exec_get_global_confidence_score(instruments_uc, confidence_uc, args: dict, user_id: int) -> dict:
    async def _call():
        instrument = await resolve_instrument(args["symbol"], instruments_uc)
        if instrument is None:
            return _error(f"instrument introuvable : {args['symbol']}")
        return _ok(await confidence_uc.execute(instrument.id, args["timeframe"]))

    return await _run(_call)


# ---------------------------------------------------------------------------
# risk_management
# ---------------------------------------------------------------------------

async def exec_get_risk_profile(instruments_uc, risk_profile_uc, args: dict, user_id: int) -> dict:
    async def _call():
        instrument = await resolve_instrument(args["symbol"], instruments_uc)
        if instrument is None:
            return _error(f"instrument introuvable : {args['symbol']}")
        return _ok(
            await risk_profile_uc.execute(
                instrument.id, args["timeframe"], capital=float(args.get("capital", 10_000.0))
            )
        )

    return await _run(_call)


async def exec_get_risk_budget(risk_budget_uc, args: dict, user_id: int) -> dict:
    async def _call():
        return _ok(await risk_budget_uc.execute())

    return await _run(_call)


# ---------------------------------------------------------------------------
# news / sentiment / explainability
# ---------------------------------------------------------------------------

async def exec_get_news(news_uc, args: dict, user_id: int) -> dict:
    async def _call():
        return _ok(await news_uc.execute(int(args.get("limit", 20))))

    return await _run(_call)


async def exec_analyze_news_sentiment(sentiment_uc, args: dict, user_id: int) -> dict:
    async def _call():
        return _ok(await sentiment_uc.execute(int(args.get("limit", 10))))

    return await _run(_call)


async def exec_analyze_news_intelligence(news_intelligence_uc, args: dict, user_id: int) -> dict:
    async def _call():
        return _ok(await news_intelligence_uc.execute(int(args.get("limit", 30))))

    return await _run(_call)


async def exec_get_news_price_correlation(instruments_uc, news_correlation_uc, args: dict, user_id: int) -> dict:
    async def _call():
        instrument = await resolve_instrument(args["symbol"], instruments_uc)
        if instrument is None:
            return _error(f"instrument introuvable : {args['symbol']}")
        return _ok(await news_correlation_uc.execute(instrument.id, int(args.get("days", 14))))

    return await _run(_call)


async def exec_get_global_feature_importance(instruments_uc, feature_importance_uc, args: dict, user_id: int) -> dict:
    async def _call():
        instrument = await resolve_instrument(args["symbol"], instruments_uc)
        if instrument is None:
            return _error(f"instrument introuvable : {args['symbol']}")
        return _ok(
            await feature_importance_uc.execute(
                instrument.id, args["timeframe"], int(args.get("limit", 50))
            )
        )

    return await _run(_call)


# ---------------------------------------------------------------------------
# portfolio_analytics / paper_trading / alert_center / settings (lecture)
# ---------------------------------------------------------------------------

async def exec_get_portfolio_summary(portfolio_summary_uc, args: dict, user_id: int) -> dict:
    async def _call():
        return _ok(await portfolio_summary_uc.execute())

    return await _run(_call)


async def exec_list_paper_sessions(manage_sessions_uc, args: dict, user_id: int) -> dict:
    async def _call():
        return _ok(await manage_sessions_uc.list_sessions())

    return await _run(_call)


async def exec_get_paper_session_detail(manage_sessions_uc, args: dict, user_id: int) -> dict:
    async def _call():
        return _ok(await manage_sessions_uc.detail(int(args["session_id"])))

    return await _run(_call)


async def exec_list_alerts(manage_alerts_uc, args: dict, user_id: int) -> dict:
    async def _call():
        return _ok(await manage_alerts_uc.list_alerts())

    return await _run(_call)


async def exec_get_settings(settings_uc, args: dict, user_id: int) -> dict:
    async def _call():
        return _ok(await settings_uc.execute(user_id))

    return await _run(_call)


# ---------------------------------------------------------------------------
# Actions d'écriture
# ---------------------------------------------------------------------------

async def exec_create_alert(instruments_uc, manage_alerts_uc, args: dict, user_id: int) -> dict:
    from src.modules.alert_center.application.use_cases.manage_alerts import (
        CreateAlertRequest,
    )

    async def _call():
        instrument = await resolve_instrument(args["symbol"], instruments_uc)
        if instrument is None:
            return _error(f"instrument introuvable : {args['symbol']}")
        request = CreateAlertRequest(
            instrument_id=instrument.id,
            timeframe=args.get("timeframe", "1m"),
            condition_type=args["condition_type"],
            threshold=float(args["threshold"]),
        )
        return _ok(await manage_alerts_uc.create(request))

    return await _run(_call)


async def exec_delete_alert(manage_alerts_uc, args: dict, user_id: int) -> dict:
    async def _call():
        await manage_alerts_uc.delete(int(args["alert_id"]))
        return {"ok": True, "deleted_alert_id": int(args["alert_id"])}

    return await _run(_call)


async def exec_create_paper_trading_session(instruments_uc, manage_sessions_uc, args: dict, user_id: int) -> dict:
    from src.modules.backtesting.application.dto import StrategySpec
    from src.modules.paper_trading.application.dto import CreateSessionRequest

    async def _call():
        instrument = await resolve_instrument(args["symbol"], instruments_uc)
        if instrument is None:
            return _error(f"instrument introuvable : {args['symbol']}")
        request = CreateSessionRequest(
            instrument_id=instrument.id,
            timeframe=args["timeframe"],
            strategy=StrategySpec(type=args.get("strategy_type", "sma_crossover")),
            initial_capital=float(args.get("initial_capital", 10_000.0)),
        )
        return _ok(await manage_sessions_uc.create(request))

    return await _run(_call)


async def exec_stop_paper_trading_session(manage_sessions_uc, args: dict, user_id: int) -> dict:
    async def _call():
        return _ok(await manage_sessions_uc.stop(int(args["session_id"])))

    return await _run(_call)


async def exec_update_setting(update_setting_uc, args: dict, user_id: int) -> dict:
    async def _call():
        key = args["key"]
        if key not in _ALLOWED_SETTING_KEYS:
            return _error(f"clé de paramètre non autorisée : {key}")
        return _ok(await update_setting_uc.execute(user_id, key, str(args["value"])))

    return await _run(_call)


async def exec_start_training(instruments_uc, manage_training_uc, args: dict, user_id: int) -> dict:
    async def _call():
        instrument = await resolve_instrument(args["symbol"], instruments_uc)
        if instrument is None:
            return _error(f"instrument introuvable : {args['symbol']}")
        return _ok(await manage_training_uc.start(args["timeframe"], [instrument.id]))

    return await _run(_call)


async def exec_stop_training(instruments_uc, manage_training_uc, args: dict, user_id: int) -> dict:
    async def _call():
        instrument = await resolve_instrument(args["symbol"], instruments_uc)
        if instrument is None:
            return _error(f"instrument introuvable : {args['symbol']}")
        return _ok(await manage_training_uc.stop(args["timeframe"], [instrument.id]))

    return await _run(_call)


async def exec_optimize_model_hyperparameters(instruments_uc, optimize_model_uc, args: dict, user_id: int) -> dict:
    from src.modules.hyperparameter_optimization.application.dto import (
        OptimizeModelRequest,
    )

    async def _call():
        instrument = await resolve_instrument(args["symbol"], instruments_uc)
        if instrument is None:
            return _error(f"instrument introuvable : {args['symbol']}")
        request = OptimizeModelRequest(
            instrument_id=instrument.id,
            timeframe=args["timeframe"],
            n_trials=int(args.get("n_trials", 15)),
        )
        return _ok(await optimize_model_uc.execute(request))

    return await _run(_call)
