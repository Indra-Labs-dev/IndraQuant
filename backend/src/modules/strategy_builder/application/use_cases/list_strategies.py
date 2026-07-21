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
}


class ListStrategiesUseCase:
    def execute(self) -> StrategiesResponse:
        return StrategiesResponse(
            strategies=[_DEFINITIONS[t] for t in STRATEGY_TYPES]
        )
