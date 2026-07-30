from dataclasses import dataclass
from functools import partial
from typing import Awaitable, Callable

from src.modules.ai_assistant.application.tools import executors as ex
from src.modules.ai_assistant.application.tools.schemas import TOOL_SPECS, ToolSpec

Dispatch = Callable[[dict, int], Awaitable[dict]]


@dataclass(frozen=True)
class ToolRegistry:
    specs: dict[str, ToolSpec]
    dispatch: dict[str, Dispatch]


def build_tool_registry(use_cases: dict[str, object]) -> ToolRegistry:
    """`use_cases` holds already-constructed use-case instances, built once
    in composition_root.py (the only place that already imports every
    module) — this function only binds them to their executor via
    `functools.partial`, so this package never imports another module's
    provider directly (see ai_assistant tool-calling plan)."""
    uc = use_cases
    dispatch: dict[str, Dispatch] = {
        "list_instruments": partial(ex.exec_list_instruments, uc["instruments"]),
        "get_market_status": partial(ex.exec_get_market_status, uc["instruments"], uc["market_status"]),
        "get_ohlcv": partial(ex.exec_get_ohlcv, uc["instruments"], uc["ohlcv"]),
        "compute_indicators": partial(ex.exec_compute_indicators, uc["instruments"], uc["compute_indicators"]),
        "get_volume_profile": partial(ex.exec_get_volume_profile, uc["instruments"], uc["volume_profile"]),
        "detect_patterns": partial(ex.exec_detect_patterns, uc["instruments"], uc["detect_patterns"]),
        "detect_smc": partial(ex.exec_detect_smc, uc["instruments"], uc["detect_smc"]),
        "predict_direction": partial(ex.exec_predict_direction, uc["instruments"], uc["predict_direction"]),
        "get_prediction_dashboard": partial(ex.exec_get_prediction_dashboard, uc["instruments"], uc["prediction_dashboard"]),
        "get_market_regime": partial(ex.exec_get_market_regime, uc["instruments"], uc["market_regime"]),
        "get_correlation_matrix": partial(ex.exec_get_correlation_matrix, uc["instruments"], uc["correlation_matrix"]),
        "get_meta_decision": partial(ex.exec_get_meta_decision, uc["instruments"], uc["meta_decision"]),
        "get_global_confidence_score": partial(ex.exec_get_global_confidence_score, uc["instruments"], uc["global_confidence"]),
        "get_risk_profile": partial(ex.exec_get_risk_profile, uc["instruments"], uc["risk_profile"]),
        "get_risk_budget": partial(ex.exec_get_risk_budget, uc["risk_budget"]),
        "get_news": partial(ex.exec_get_news, uc["news"]),
        "analyze_news_sentiment": partial(ex.exec_analyze_news_sentiment, uc["sentiment"]),
        "analyze_news_intelligence": partial(ex.exec_analyze_news_intelligence, uc["news_intelligence"]),
        "get_news_price_correlation": partial(ex.exec_get_news_price_correlation, uc["instruments"], uc["news_correlation"]),
        "get_global_feature_importance": partial(ex.exec_get_global_feature_importance, uc["instruments"], uc["feature_importance"]),
        "get_portfolio_summary": partial(ex.exec_get_portfolio_summary, uc["portfolio_summary"]),
        "list_paper_sessions": partial(ex.exec_list_paper_sessions, uc["manage_sessions"]),
        "get_paper_session_detail": partial(ex.exec_get_paper_session_detail, uc["manage_sessions"]),
        "list_alerts": partial(ex.exec_list_alerts, uc["manage_alerts"]),
        "get_settings": partial(ex.exec_get_settings, uc["settings"]),
        "create_alert": partial(ex.exec_create_alert, uc["instruments"], uc["manage_alerts"]),
        "delete_alert": partial(ex.exec_delete_alert, uc["manage_alerts"]),
        "create_paper_trading_session": partial(ex.exec_create_paper_trading_session, uc["instruments"], uc["manage_sessions"]),
        "stop_paper_trading_session": partial(ex.exec_stop_paper_trading_session, uc["manage_sessions"]),
        "update_setting": partial(ex.exec_update_setting, uc["update_setting"]),
        "start_training": partial(ex.exec_start_training, uc["instruments"], uc["manage_training"]),
        "stop_training": partial(ex.exec_stop_training, uc["instruments"], uc["manage_training"]),
        "optimize_model_hyperparameters": partial(ex.exec_optimize_model_hyperparameters, uc["instruments"], uc["optimize_model"]),
    }
    assert set(dispatch) == set(TOOL_SPECS), (
        f"registry/schema mismatch: {set(dispatch) ^ set(TOOL_SPECS)}"
    )
    return ToolRegistry(specs=TOOL_SPECS, dispatch=dispatch)
