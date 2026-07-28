from src.modules.settings.application.dto import SettingsResponse
from src.modules.settings.domain.repositories import SettingsRepository


class GetSettingsUseCase:
    def __init__(self, settings_repo: SettingsRepository) -> None:
        self._settings = settings_repo

    async def execute(self, user_id: int) -> SettingsResponse:
        return SettingsResponse(
            settings={s.key: s.value for s in await self._settings.get_all(user_id)}
        )
