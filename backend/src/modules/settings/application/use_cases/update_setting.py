from src.modules.settings.application.dto import SettingsResponse
from src.modules.settings.domain.repositories import SettingsRepository


class UpdateSettingUseCase:
    def __init__(self, settings_repo: SettingsRepository) -> None:
        self._settings = settings_repo

    def execute(self, user_id: int, key: str, value: str) -> SettingsResponse:
        self._settings.upsert(user_id, key, value)
        return SettingsResponse(
            settings={s.key: s.value for s in self._settings.get_all(user_id)}
        )
