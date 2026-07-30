from pydantic import BaseModel

from src.modules.ai_assistant.domain.repositories import MemoryRepository


class MemoryResponse(BaseModel):
    facts: list[str]


class GetMemoryUseCase:
    def __init__(self, memory_repository: MemoryRepository) -> None:
        self._memory_repository = memory_repository

    async def execute(self, user_id: int) -> MemoryResponse:
        facts = await self._memory_repository.list_facts(user_id)
        return MemoryResponse(facts=[f.content for f in facts])


class ClearMemoryUseCase:
    def __init__(self, memory_repository: MemoryRepository) -> None:
        self._memory_repository = memory_repository

    async def execute(self, user_id: int) -> MemoryResponse:
        await self._memory_repository.replace_facts(user_id, [])
        return MemoryResponse(facts=[])
