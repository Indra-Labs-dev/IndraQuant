from pydantic import BaseModel


class KellyDto(BaseModel):
    fraction: float
    has_edge: bool
    explanation: str


class PositionSizeDto(BaseModel):
    quantity: float
    risk_amount: float
    position_value: float
    capital_at_risk_pct: float
    explanation: str


class StressScenarioDto(BaseModel):
    shock_pct: float
    resulting_value: float
    loss_amount: float


class RiskProfileResponse(BaseModel):
    instrument_id: int
    timeframe: str
    var_95: float | None
    expected_shortfall_95: float | None
    max_drawdown: float
    annualized_volatility: float | None
    kelly: KellyDto
    risk_of_ruin: float
    position_sizing: PositionSizeDto
    stress_test: list[StressScenarioDto]
    explanation: str


class ExposureWarningDto(BaseModel):
    instrument: str
    weight_pct: float
    limit_pct: float
    message: str


class ExposureReportResponse(BaseModel):
    warnings: list[ExposureWarningDto]
    total_exposure_pct: float
    max_single_pct: float
    max_total_pct: float
    explanation: str


class RiskBudgetItemDto(BaseModel):
    instrument_id: int
    symbol: str
    current_weight_pct: float
    target_weight_pct: float
    annualized_volatility: float | None


class RiskBudgetResponse(BaseModel):
    items: list[RiskBudgetItemDto]
    explanation: str
