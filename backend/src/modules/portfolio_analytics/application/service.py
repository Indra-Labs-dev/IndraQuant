from datetime import datetime

from pydantic import BaseModel


class TradeRecord(BaseModel):
    side: str
    quantity: float
    price: float
    fee: float
    executed_at: datetime
    reason: str


class PortfolioAnalytics(BaseModel):
    equity: float
    cash: float
    position_quantity: float
    position_value: float
    pnl: float
    return_pct: float
    fees_paid: float
    trade_count: int


def compute_analytics(
    initial_capital: float,
    cash: float,
    position_quantity: float,
    last_price: float,
    trades: list[TradeRecord],
) -> PortfolioAnalytics:
    position_value = position_quantity * last_price
    equity = cash + position_value
    return PortfolioAnalytics(
        equity=equity,
        cash=cash,
        position_quantity=position_quantity,
        position_value=position_value,
        pnl=equity - initial_capital,
        return_pct=(equity / initial_capital - 1.0) if initial_capital > 0 else 0.0,
        fees_paid=sum(t.fee for t in trades),
        trade_count=len(trades),
    )
