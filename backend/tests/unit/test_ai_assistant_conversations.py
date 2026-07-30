from datetime import datetime, timedelta, timezone

from src.modules.ai_assistant.application.use_cases.list_conversations import (
    ListConversationsUseCase,
)
from src.modules.ai_assistant.domain.entities import Conversation


class FakeConversationRepository:
    def __init__(self, conversations: list[Conversation]) -> None:
        self._conversations = conversations

    async def list_conversations(self, user_id: int) -> list[Conversation]:
        return sorted(
            self._conversations, key=lambda c: c.updated_at, reverse=True
        )

    async def create_conversation(self, user_id: int, title: str) -> Conversation:
        raise NotImplementedError


async def test_list_conversations_orders_most_recently_updated_first():
    now = datetime.now(timezone.utc)
    older = Conversation(id=1, title="Ancienne", updated_at=now - timedelta(hours=2))
    newer = Conversation(id=2, title="Récente", updated_at=now)
    repository = FakeConversationRepository([older, newer])

    response = await ListConversationsUseCase(repository).execute(1)

    assert [c.id for c in response.conversations] == [2, 1]
    assert response.conversations[0].title == "Récente"


async def test_list_conversations_empty_when_none_exist():
    repository = FakeConversationRepository([])

    response = await ListConversationsUseCase(repository).execute(1)

    assert response.conversations == []
