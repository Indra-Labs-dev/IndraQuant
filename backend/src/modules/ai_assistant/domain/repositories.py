from typing import Protocol

from src.modules.ai_assistant.domain.entities import ChatMessageRecord, MemoryFact


class ChatRepository(Protocol):
    async def add_message(self, user_id: int, role: str, content: str) -> None: ...

    async def list_recent(self, user_id: int, limit: int) -> list[ChatMessageRecord]: ...


class MemoryRepository(Protocol):
    async def list_facts(self, user_id: int) -> list[MemoryFact]: ...

    async def replace_facts(self, user_id: int, facts: list[str]) -> None: ...
