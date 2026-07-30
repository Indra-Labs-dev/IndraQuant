from pydantic import BaseModel

from src.modules.ai_assistant.application.use_cases.chat import ChatMessage
from src.modules.ai_assistant.domain.repositories import ChatRepository

_HISTORY_LIMIT = 200


class ChatHistoryResponse(BaseModel):
    messages: list[ChatMessage]


class GetChatHistoryUseCase:
    def __init__(self, chat_repository: ChatRepository) -> None:
        self._chat_repository = chat_repository

    async def execute(self, user_id: int) -> ChatHistoryResponse:
        history = await self._chat_repository.list_recent(user_id, _HISTORY_LIMIT)
        return ChatHistoryResponse(
            messages=[ChatMessage(role=h.role, content=h.content) for h in history]
        )
