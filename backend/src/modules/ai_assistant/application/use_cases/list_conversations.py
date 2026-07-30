from datetime import datetime

from pydantic import BaseModel

from src.modules.ai_assistant.domain.repositories import ConversationRepository


class ConversationSummaryDto(BaseModel):
    id: int
    title: str | None
    updated_at: datetime


class ConversationsResponse(BaseModel):
    conversations: list[ConversationSummaryDto]


class ListConversationsUseCase:
    def __init__(self, conversation_repository: ConversationRepository) -> None:
        self._conversation_repository = conversation_repository

    async def execute(self, user_id: int) -> ConversationsResponse:
        conversations = await self._conversation_repository.list_conversations(user_id)
        return ConversationsResponse(
            conversations=[
                ConversationSummaryDto(id=c.id, title=c.title, updated_at=c.updated_at)
                for c in conversations
            ]
        )
