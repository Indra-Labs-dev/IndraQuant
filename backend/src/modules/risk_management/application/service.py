from pydantic import BaseModel

from src.modules.risk_management.domain import metrics


class RiskReport(BaseModel):
    var_95: float | None
    max_drawdown: float
    annualized_volatility: float | None
    explanation: str


def compute_risk(equity: list[float], periods_per_year: float) -> RiskReport:
    returns = metrics.period_returns(equity)
    var = metrics.historical_var(returns)
    drawdown = metrics.max_drawdown(equity)
    volatility = metrics.annualized_volatility(returns, periods_per_year)
    var_text = (
        f"VaR 95 % : perte par période ≤ {var * 100:.2f} % dans 95 % des cas observés"
        if var is not None
        else "VaR 95 % : historique insuffisant (moins de 20 périodes)"
    )
    return RiskReport(
        var_95=var,
        max_drawdown=drawdown,
        annualized_volatility=volatility,
        explanation=(
            f"{var_text}. Drawdown maximal observé {drawdown * 100:.2f} %. "
            "Estimations historiques : elles décrivent le passé de la courbe "
            "de capital, pas une garantie future."
        ),
    )
