from pydantic import BaseModel

from src.modules.backtesting.application.service import STRATEGY_TYPES


class StrategyParameter(BaseModel):
    name: str
    label: str
    default: float
    min: float
    max: float


class StrategyDefinition(BaseModel):
    type: str
    label: str
    description: str
    parameters: list[StrategyParameter]


class StrategiesResponse(BaseModel):
    strategies: list[StrategyDefinition]


_DEFINITIONS = {
    "sma_crossover": StrategyDefinition(
        type="sma_crossover",
        label="Croisement de moyennes mobiles",
        description=(
            "Achète quand la moyenne mobile rapide passe au-dessus de la "
            "lente, vend quand elle repasse en dessous."
        ),
        parameters=[
            StrategyParameter(name="fast", label="MM rapide", default=20, min=2, max=500),
            StrategyParameter(name="slow", label="MM lente", default=50, min=3, max=1000),
        ],
    ),
    "rsi_reversion": StrategyDefinition(
        type="rsi_reversion",
        label="Retour à la moyenne (RSI)",
        description=(
            "Achète quand le RSI passe sous le seuil bas (survente), vend "
            "quand il dépasse le seuil haut (surachat)."
        ),
        parameters=[
            StrategyParameter(name="period", label="Période RSI", default=14, min=2, max=100),
            StrategyParameter(name="low", label="Seuil bas", default=30, min=1, max=99),
            StrategyParameter(name="high", label="Seuil haut", default=70, min=1, max=99),
        ],
    ),
    "macd_crossover": StrategyDefinition(
        type="macd_crossover",
        label="Croisement MACD",
        description=(
            "Achète quand la ligne MACD passe au-dessus de sa ligne de "
            "signal, vend quand elle repasse en dessous — capte les "
            "changements de momentum plus tôt qu'un simple croisement de "
            "moyennes mobiles."
        ),
        parameters=[
            StrategyParameter(name="fast", label="EMA rapide", default=12, min=2, max=100),
            StrategyParameter(name="slow", label="EMA lente", default=26, min=3, max=200),
            StrategyParameter(name="signal", label="Ligne de signal", default=9, min=2, max=50),
        ],
    ),
    "bollinger_breakout": StrategyDefinition(
        type="bollinger_breakout",
        label="Cassure de Bollinger",
        description=(
            "Achète quand le prix clôture au-dessus de la bande de "
            "Bollinger supérieure (cassure haussière), vend quand il "
            "repasse sous la bande médiane — suivi de tendance, à "
            "l'opposé du retour à la moyenne RSI."
        ),
        parameters=[
            StrategyParameter(name="period", label="Période", default=20, min=5, max=100),
            StrategyParameter(name="num_std", label="Écart-type (σ)", default=2, min=0.5, max=5),
        ],
    ),
}


class ListStrategiesUseCase:
    def execute(self) -> StrategiesResponse:
        return StrategiesResponse(
            strategies=[_DEFINITIONS[t] for t in STRATEGY_TYPES]
        )
