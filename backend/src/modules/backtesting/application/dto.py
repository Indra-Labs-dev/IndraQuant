from datetime import datetime

from pydantic import BaseModel, Field


class StrategySpec(BaseModel):
    type: str = "sma_crossover"
    # sma_crossover parameters
    fast: int = Field(default=20, ge=2, le=500)
    slow: int = Field(default=50, ge=3, le=1000)
    # rsi_reversion parameters
    period: int = Field(default=14, ge=2, le=100)
    low: float = Field(default=30.0, ge=1, le=99)
    high: float = Field(default=70.0, ge=1, le=99)


class RunBacktestRequest(BaseModel):
    instrument_id: int
    timeframe: str
    from_: datetime = Field(alias="from")
    to: datetime
    strategy: StrategySpec = StrategySpec()
    initial_capital: float = Field(default=10_000.0, gt=0)


class TradeDto(BaseModel):
    side: str
    time: datetime
    price: float
    quantity: float
    fee: float
    reason: str


class EquityPoint(BaseModel):
    time: datetime
    equity: float


class BacktestReport(BaseModel):
    id: int | None = None
    instrument_id: int
    timeframe: str
    strategy: StrategySpec
    initial_capital: float
    final_equity: float
    total_return: float
    max_drawdown: float
    sharpe: float | None
    win_rate: float | None
    trade_count: int
    trades: list[TradeDto]
    equity_curve: list[EquityPoint]
    explanation: str


class BacktestSummary(BaseModel):
    id: int
    instrument_id: int
    timeframe: str
    strategy: StrategySpec
    initial_capital: float
    final_equity: float
    total_return: float
    max_drawdown: float
    trade_count: int
    created_at: datetime


class BacktestListResponse(BaseModel):
    backtests: list[BacktestSummary]


class WalkForwardRequest(RunBacktestRequest):
    folds: int = Field(default=4, ge=2, le=10)


class WalkForwardFold(BaseModel):
    fold: int
    best_fast: int
    best_slow: int
    train_return: float
    test_return: float


class WalkForwardReport(BaseModel):
    instrument_id: int
    timeframe: str
    folds: list[WalkForwardFold]
    mean_test_return: float
    positive_test_folds: int
    total_folds: int
    explanation: str
