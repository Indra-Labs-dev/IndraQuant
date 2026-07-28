from src.modules.settings.application.use_cases.get_settings import GetSettingsUseCase
from src.modules.settings.application.use_cases.update_setting import (
    UpdateSettingUseCase,
)
from src.modules.settings.domain.entities import Setting


class FakeSettingsRepository:
    def __init__(self) -> None:
        self._data: dict[tuple[int, str], str] = {}

    async def get_all(self, user_id: int) -> list[Setting]:
        return [
            Setting(key=key, value=value)
            for (uid, key), value in self._data.items()
            if uid == user_id
        ]

    async def upsert(self, user_id: int, key: str, value: str) -> Setting:
        self._data[(user_id, key)] = value
        return Setting(key=key, value=value)


async def test_get_settings_returns_key_value_map():
    repo = FakeSettingsRepository()
    await repo.upsert(1, "language", "fr")
    await repo.upsert(2, "language", "en")

    response = await GetSettingsUseCase(repo).execute(1)

    assert response.settings == {"language": "fr"}


async def test_update_setting_upserts_and_returns_full_map():
    repo = FakeSettingsRepository()
    await repo.upsert(1, "language", "fr")

    response = await UpdateSettingUseCase(repo).execute(1, "theme", "dark")

    assert response.settings == {"language": "fr", "theme": "dark"}
