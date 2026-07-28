from typing import Protocol

from src.modules.settings.domain.entities import Setting


class SettingsRepository(Protocol):
    async def get_all(self, user_id: int) -> list[Setting]: ...

    async def upsert(self, user_id: int, key: str, value: str) -> Setting: ...
