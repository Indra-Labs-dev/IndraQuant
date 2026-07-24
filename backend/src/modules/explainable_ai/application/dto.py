from datetime import datetime

from pydantic import BaseModel


class ShapSnapshotDto(BaseModel):
    prediction_id: int
    as_of: datetime
    predicted_direction: str
    contributions: list["FeatureContributionDto"]


class FeatureContributionDto(BaseModel):
    feature: str
    value: float
    contribution: float


class ShapHistoryResponse(BaseModel):
    instrument_id: int
    timeframe: str
    snapshots: list[ShapSnapshotDto]
    explanation: str


class GlobalImportanceItemDto(BaseModel):
    feature: str
    mean_absolute_contribution: float
    rank: int


class GlobalImportanceResponse(BaseModel):
    instrument_id: int
    timeframe: str
    sample_size: int
    items: list[GlobalImportanceItemDto]
    explanation: str


class FeatureTimePointDto(BaseModel):
    as_of: datetime
    contribution: float


class FeatureEvolutionResponse(BaseModel):
    instrument_id: int
    timeframe: str
    feature: str
    points: list[FeatureTimePointDto]
    explanation: str


class ExplanationDeltaDto(BaseModel):
    feature: str
    contribution_a: float
    contribution_b: float
    delta: float


class CompareExplanationsResponse(BaseModel):
    prediction_id_a: int
    prediction_id_b: int
    similarity: float | None
    deltas: list[ExplanationDeltaDto]
    explanation: str
