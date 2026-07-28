from fastapi import APIRouter, Depends

from src.composition_root import (
    get_current_user,
    get_settings_use_case,
    get_update_setting_use_case,
)
from src.modules.auth.application.dto import UserProfile
from src.modules.settings.application.dto import SettingsResponse, UpdateSettingRequest
from src.modules.settings.application.use_cases.get_settings import GetSettingsUseCase
from src.modules.settings.application.use_cases.update_setting import (
    UpdateSettingUseCase,
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
async def get_settings(
    user: UserProfile = Depends(get_current_user),
    use_case: GetSettingsUseCase = Depends(get_settings_use_case),
) -> SettingsResponse:
    return await use_case.execute(user.id)


@router.put("/{key}")
async def update_setting(
    key: str,
    request: UpdateSettingRequest,
    user: UserProfile = Depends(get_current_user),
    use_case: UpdateSettingUseCase = Depends(get_update_setting_use_case),
) -> SettingsResponse:
    return await use_case.execute(user.id, key, request.value)
