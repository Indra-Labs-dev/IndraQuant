from dataclasses import dataclass

_TIMEFRAME_DESC = (
    "unité de temps, ex: 1m, 5m, 15m, 1h, 4h, 1d"
)
_SYMBOL_DESC = (
    "symbole de l'instrument tel qu'affiché dans l'application, ex: BTC/USDT, AAPL"
)
_INDICATOR_NAMES = [
    "sma", "ema", "rsi", "bollinger", "vwap", "atr", "adx", "donchian",
    "keltner", "mfi", "cci", "williams_r", "cmf", "ulcer", "momentum",
    "volatility_clustering",
]
_STRATEGY_TYPES = ["sma_crossover", "rsi_reversion", "macd_crossover", "bollinger_breakout"]
_ALERT_CONDITIONS = ["price_above", "price_below", "rsi_above", "rsi_below"]
_SETTING_KEYS = ["theme", "language", "ai_temperature", "ai_max_tokens", "ai_tools_enabled"]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict
    is_write: bool = False


def _obj(properties: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": properties, "required": required}


# ---------------------------------------------------------------------------
# market_data / technical_analysis
# ---------------------------------------------------------------------------
_MARKET_DATA_TOOLS = [
    ToolSpec(
        "list_instruments",
        "Liste tous les instruments suivis (crypto, actions) avec leur symbole.",
        _obj({}, []),
    ),
    ToolSpec(
        "get_market_status",
        "Indique si le marché d'un instrument est actuellement ouvert (utile pour les actions, les cryptos sont ouvertes 24/7).",
        _obj({"symbol": {"type": "string", "description": _SYMBOL_DESC}}, ["symbol"]),
    ),
    ToolSpec(
        "get_ohlcv",
        "Retourne les dernières bougies (prix ouverture/haut/bas/clôture/volume) d'un instrument.",
        _obj(
            {
                "symbol": {"type": "string", "description": _SYMBOL_DESC},
                "timeframe": {"type": "string", "description": _TIMEFRAME_DESC},
                "limit": {"type": "integer", "description": "nombre de bougies, défaut 100"},
            },
            ["symbol", "timeframe"],
        ),
    ),
    ToolSpec(
        "compute_indicators",
        "Calcule un ou plusieurs indicateurs techniques pour un instrument.",
        _obj(
            {
                "symbol": {"type": "string", "description": _SYMBOL_DESC},
                "timeframe": {"type": "string", "description": _TIMEFRAME_DESC},
                "indicators": {
                    "type": "array",
                    "items": {"type": "string", "enum": _INDICATOR_NAMES},
                    "description": "liste d'indicateurs parmi: " + ", ".join(_INDICATOR_NAMES),
                },
                "limit": {"type": "integer", "description": "nombre de bougies, défaut 200"},
            },
            ["symbol", "timeframe", "indicators"],
        ),
    ),
    ToolSpec(
        "get_volume_profile",
        "Retourne l'histogramme du volume échangé par niveau de prix et le point de contrôle (prix le plus échangé).",
        _obj(
            {
                "symbol": {"type": "string", "description": _SYMBOL_DESC},
                "timeframe": {"type": "string", "description": _TIMEFRAME_DESC},
                "limit": {"type": "integer", "description": "nombre de bougies, défaut 200"},
            },
            ["symbol", "timeframe"],
        ),
    ),
    ToolSpec(
        "detect_patterns",
        "Détecte des figures chartistes (engulfing, marteau, double sommet) sur les dernières bougies.",
        _obj(
            {
                "symbol": {"type": "string", "description": _SYMBOL_DESC},
                "timeframe": {"type": "string", "description": _TIMEFRAME_DESC},
                "limit": {"type": "integer", "description": "nombre de bougies, défaut 200"},
            },
            ["symbol", "timeframe"],
        ),
    ),
    ToolSpec(
        "detect_smc",
        "Détecte des concepts Smart Money (order blocks, fair value gaps, liquidity sweeps) sur les dernières bougies.",
        _obj(
            {
                "symbol": {"type": "string", "description": _SYMBOL_DESC},
                "timeframe": {"type": "string", "description": _TIMEFRAME_DESC},
                "limit": {"type": "integer", "description": "nombre de bougies, défaut 200"},
            },
            ["symbol", "timeframe"],
        ),
    ),
]

# ---------------------------------------------------------------------------
# prediction_engine / market_regime / correlation_engine / meta_decision /
# confidence_score
# ---------------------------------------------------------------------------
_ANALYSIS_TOOLS = [
    ToolSpec(
        "predict_direction",
        "Prédit la probabilité de hausse/baisse du prochain mouvement de prix pour un instrument (modèle ML, avec explication SHAP).",
        _obj(
            {
                "symbol": {"type": "string", "description": _SYMBOL_DESC},
                "timeframe": {"type": "string", "description": _TIMEFRAME_DESC},
            },
            ["symbol", "timeframe"],
        ),
    ),
    ToolSpec(
        "get_prediction_dashboard",
        "Retourne le bilan réel des prédictions passées (précision, calibration) pour une unité de temps, éventuellement un instrument précis.",
        _obj(
            {
                "timeframe": {"type": "string", "description": _TIMEFRAME_DESC},
                "symbol": {"type": "string", "description": _SYMBOL_DESC + " (optionnel)"},
                "limit": {"type": "integer", "description": "nombre de prédictions récentes, défaut 50"},
            },
            ["timeframe"],
        ),
    ),
    ToolSpec(
        "get_market_regime",
        "Indique le régime de marché actuel d'un instrument (tendance/range, volatilité normale/élevée, panique).",
        _obj(
            {
                "symbol": {"type": "string", "description": _SYMBOL_DESC},
                "timeframe": {"type": "string", "description": _TIMEFRAME_DESC},
            },
            ["symbol", "timeframe"],
        ),
    ),
    ToolSpec(
        "get_correlation_matrix",
        "Calcule la corrélation entre plusieurs instruments sur une période.",
        _obj(
            {
                "symbols": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "au moins deux symboles, ex: [\"BTC/USDT\", \"ETH/USDT\"]",
                },
                "timeframe": {"type": "string", "description": _TIMEFRAME_DESC},
            },
            ["symbols", "timeframe"],
        ),
    ),
    ToolSpec(
        "get_meta_decision",
        "Fusionne plusieurs moteurs d'analyse (tendance, ML, SMC, news, régime) en une décision explicable unique pour un instrument.",
        _obj(
            {
                "symbol": {"type": "string", "description": _SYMBOL_DESC},
                "timeframe": {"type": "string", "description": _TIMEFRAME_DESC},
            },
            ["symbol", "timeframe"],
        ),
    ),
    ToolSpec(
        "get_global_confidence_score",
        "Retourne un score de confiance global (0-100) résumant la fiabilité de l'analyse actuelle pour un instrument.",
        _obj(
            {
                "symbol": {"type": "string", "description": _SYMBOL_DESC},
                "timeframe": {"type": "string", "description": _TIMEFRAME_DESC},
            },
            ["symbol", "timeframe"],
        ),
    ),
]

# ---------------------------------------------------------------------------
# risk_management
# ---------------------------------------------------------------------------
_RISK_TOOLS = [
    ToolSpec(
        "get_risk_profile",
        "Calcule le profil de risque d'un instrument (VaR, Kelly, taille de position recommandée, stress test).",
        _obj(
            {
                "symbol": {"type": "string", "description": _SYMBOL_DESC},
                "timeframe": {"type": "string", "description": _TIMEFRAME_DESC},
                "capital": {"type": "number", "description": "capital de référence en USD, défaut 10000"},
            },
            ["symbol", "timeframe"],
        ),
    ),
    ToolSpec(
        "get_risk_budget",
        "Retourne la répartition actuelle du risque entre les positions de paper trading en cours.",
        _obj({}, []),
    ),
]

# ---------------------------------------------------------------------------
# news / sentiment / explainability
# ---------------------------------------------------------------------------
_NEWS_TOOLS = [
    ToolSpec(
        "get_news",
        "Retourne les dernières actualités financières.",
        _obj({"limit": {"type": "integer", "description": "défaut 20"}}, []),
    ),
    ToolSpec(
        "analyze_news_sentiment",
        "Analyse le sentiment (positif/négatif/neutre) des dernières actualités financières.",
        _obj({"limit": {"type": "integer", "description": "défaut 10"}}, []),
    ),
    ToolSpec(
        "analyze_news_intelligence",
        "Regroupe les dernières actualités par sujet et estime leur catégorie et impact potentiel sur le marché.",
        _obj({"limit": {"type": "integer", "description": "défaut 30"}}, []),
    ),
    ToolSpec(
        "get_news_price_correlation",
        "Mesure la corrélation entre le sentiment des actualités et le mouvement de prix d'un instrument.",
        _obj(
            {
                "symbol": {"type": "string", "description": _SYMBOL_DESC},
                "days": {"type": "integer", "description": "fenêtre en jours, défaut 14"},
            },
            ["symbol"],
        ),
    ),
    ToolSpec(
        "get_global_feature_importance",
        "Retourne les features les plus influentes dans les prédictions récentes d'un instrument (explicabilité SHAP).",
        _obj(
            {
                "symbol": {"type": "string", "description": _SYMBOL_DESC},
                "timeframe": {"type": "string", "description": _TIMEFRAME_DESC},
                "limit": {"type": "integer", "description": "défaut 50"},
            },
            ["symbol", "timeframe"],
        ),
    ),
]

# ---------------------------------------------------------------------------
# portfolio_analytics / paper_trading / alert_center / settings (read side)
# ---------------------------------------------------------------------------
_PORTFOLIO_TOOLS = [
    ToolSpec(
        "get_portfolio_summary",
        "Retourne un résumé du portefeuille de paper trading (équité totale, PnL, répartition par instrument).",
        _obj({}, []),
    ),
    ToolSpec(
        "list_paper_sessions",
        "Liste les sessions de paper trading (en cours ou arrêtées).",
        _obj({}, []),
    ),
    ToolSpec(
        "get_paper_session_detail",
        "Retourne le détail d'une session de paper trading (trades, analytique, risque).",
        _obj({"session_id": {"type": "integer"}}, ["session_id"]),
    ),
    ToolSpec(
        "list_alerts",
        "Liste les alertes de prix/indicateur configurées.",
        _obj({}, []),
    ),
    ToolSpec(
        "get_settings",
        "Retourne les réglages actuels de l'application (langue, thème, paramètres de l'assistant).",
        _obj({}, []),
    ),
]

# ---------------------------------------------------------------------------
# Actions d'écriture (périmètre choisi par l'utilisateur)
# ---------------------------------------------------------------------------
_WRITE_TOOLS = [
    ToolSpec(
        "create_alert",
        "Crée une alerte de prix ou d'indicateur pour un instrument.",
        _obj(
            {
                "symbol": {"type": "string", "description": _SYMBOL_DESC},
                "timeframe": {"type": "string", "description": _TIMEFRAME_DESC + ", défaut 1m"},
                "condition_type": {"type": "string", "enum": _ALERT_CONDITIONS},
                "threshold": {"type": "number", "description": "seuil de déclenchement"},
            },
            ["symbol", "condition_type", "threshold"],
        ),
        is_write=True,
    ),
    ToolSpec(
        "delete_alert",
        "Supprime une alerte existante.",
        _obj({"alert_id": {"type": "integer"}}, ["alert_id"]),
        is_write=True,
    ),
    ToolSpec(
        "create_paper_trading_session",
        "Démarre une session de paper trading (argent fictif) sur un instrument avec une stratégie.",
        _obj(
            {
                "symbol": {"type": "string", "description": _SYMBOL_DESC},
                "timeframe": {"type": "string", "description": _TIMEFRAME_DESC},
                "strategy_type": {"type": "string", "enum": _STRATEGY_TYPES, "description": "défaut sma_crossover"},
                "initial_capital": {"type": "number", "description": "défaut 10000"},
            },
            ["symbol", "timeframe"],
        ),
        is_write=True,
    ),
    ToolSpec(
        "stop_paper_trading_session",
        "Arrête une session de paper trading en cours.",
        _obj({"session_id": {"type": "integer"}}, ["session_id"]),
        is_write=True,
    ),
    ToolSpec(
        "update_setting",
        "Modifie un réglage de l'application.",
        _obj(
            {
                "key": {"type": "string", "enum": _SETTING_KEYS},
                "value": {"type": "string"},
            },
            ["key", "value"],
        ),
        is_write=True,
    ),
    ToolSpec(
        "start_training",
        "Démarre l'entraînement continu en arrière-plan du modèle pour un instrument/unité de temps.",
        _obj(
            {
                "symbol": {"type": "string", "description": _SYMBOL_DESC},
                "timeframe": {"type": "string", "description": _TIMEFRAME_DESC},
            },
            ["symbol", "timeframe"],
        ),
        is_write=True,
    ),
    ToolSpec(
        "stop_training",
        "Arrête l'entraînement continu en arrière-plan pour un instrument/unité de temps.",
        _obj(
            {
                "symbol": {"type": "string", "description": _SYMBOL_DESC},
                "timeframe": {"type": "string", "description": _TIMEFRAME_DESC},
            },
            ["symbol", "timeframe"],
        ),
        is_write=True,
    ),
    ToolSpec(
        "optimize_model_hyperparameters",
        "Lance une recherche d'hyperparamètres pour le modèle ML d'un instrument et applique le meilleur résultat trouvé.",
        _obj(
            {
                "symbol": {"type": "string", "description": _SYMBOL_DESC},
                "timeframe": {"type": "string", "description": _TIMEFRAME_DESC},
                "n_trials": {"type": "integer", "description": "nombre d'essais, défaut 15"},
            },
            ["symbol", "timeframe"],
        ),
        is_write=True,
    ),
]

TOOL_SPECS: dict[str, ToolSpec] = {
    spec.name: spec
    for spec in (
        _MARKET_DATA_TOOLS
        + _ANALYSIS_TOOLS
        + _RISK_TOOLS
        + _NEWS_TOOLS
        + _PORTFOLIO_TOOLS
        + _WRITE_TOOLS
    )
}


def build_ollama_tools_payload(names: set[str] | None = None) -> list[dict]:
    specs = TOOL_SPECS.values() if names is None else (
        TOOL_SPECS[n] for n in names if n in TOOL_SPECS
    )
    return [
        {
            "type": "function",
            "function": {
                "name": spec.name,
                "description": spec.description,
                "parameters": spec.parameters,
            },
        }
        for spec in specs
    ]
