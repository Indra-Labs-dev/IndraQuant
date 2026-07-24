from pydantic import BaseModel


class FeatureDriftDto(BaseModel):
    feature: str
    psi: float | None
    severity: str
    explanation: str


class LabelDriftDto(BaseModel):
    reference_up_rate: float | None
    recent_up_rate: float | None
    delta: float | None
    severity: str
    explanation: str


class ConceptDriftDto(BaseModel):
    reference_accuracy: float | None
    recent_accuracy: float | None
    reference_n: int
    recent_n: int
    delta: float | None
    severity: str
    explanation: str


class DriftReportResponse(BaseModel):
    instrument_id: int
    timeframe: str
    overall_severity: str
    feature_drifts: list[FeatureDriftDto]
    label_drift: LabelDriftDto
    concept_drift: ConceptDriftDto
    explanation: str
