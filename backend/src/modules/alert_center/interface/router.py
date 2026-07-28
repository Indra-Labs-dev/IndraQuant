from fastapi import APIRouter, Depends

from src.composition_root import get_current_user, get_manage_alerts_use_case
from src.modules.alert_center.application.use_cases.manage_alerts import (
    AlertDto,
    AlertsResponse,
    CreateAlertRequest,
    ManageAlertsUseCase,
)
from src.modules.auth.application.dto import UserProfile

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("")
async def create_alert(
    request: CreateAlertRequest,
    _: UserProfile = Depends(get_current_user),
    use_case: ManageAlertsUseCase = Depends(get_manage_alerts_use_case),
) -> AlertDto:
    return await use_case.create(request)


@router.get("")
async def list_alerts(
    _: UserProfile = Depends(get_current_user),
    use_case: ManageAlertsUseCase = Depends(get_manage_alerts_use_case),
) -> AlertsResponse:
    return await use_case.list_alerts()


@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: int,
    _: UserProfile = Depends(get_current_user),
    use_case: ManageAlertsUseCase = Depends(get_manage_alerts_use_case),
) -> dict:
    await use_case.delete(alert_id)
    return {"status": "ok"}
