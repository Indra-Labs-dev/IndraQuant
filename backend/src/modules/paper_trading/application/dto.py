from datetime import datetime

from pydantic import BaseModel, Field

from src.modules.backtesting.application.dto import StrategySpec
from src.modules.portfolio_analytics.application.service import PortfolioAnalytics
from src.modules.risk_management.application.service import RiskReport


class CreateSessionRequest(BaseModel):
    instrument_id: int
    timeframe: str
    strategy: StrategySpec = StrategySpec()
    initial_capital: float = Field(default=10_000.0, gt=0)


class PaperTradeDto(BaseModel):
    side: str
    quantity: float
    price: float
    fee: float
    executed_at: datetime
    reason: str


class SessionSummary(BaseModel):
    id: int
    instrument_id: int
    timeframe: str
    strategy: StrategySpec
    initial_capital: float
    status: str
    started_at: datetime
    stopped_at: datetime | None


class SessionDetail(SessionSummary):
    trades: list[PaperTradeDto]
    analytics: PortfolioAnalytics
    risk: RiskReport


class SessionsResponse(BaseModel):
    sessions: list[SessionSummary]
