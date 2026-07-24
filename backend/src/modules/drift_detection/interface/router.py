from fastapi import APIRouter, Depends, Query

from src.composition_root import get_current_user, get_drift_report_use_case
from src.modules.auth.application.dto import UserProfile
from src.modules.drift_detection.application.dto import DriftReportResponse
from src.modules.drift_detection.application.use_cases.get_drift_report import (
    GetDriftReportUseCase,
)

router = APIRouter(tags=["drift-detection"])


@router.get("/instruments/{instrument_id}/drift")
def get_drift_report(
    instrument_id: int,
    timeframe: str = Query(default="1h"),
    _: UserProfile = Depends(get_current_user),
    use_case: GetDriftReportUseCase = Depends(get_drift_report_use_case),
) -> DriftReportResponse:
    return use_case.execute(instrument_id, timeframe)
