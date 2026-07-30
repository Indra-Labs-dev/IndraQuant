from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    delete,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.ai_assistant.domain.entities import (
    ChatMessageRecord,
    Conversation,
    MemoryFact,
)
from src.shared.infrastructure.database import Base


class ConversationModel(Base):
    __tablename__ = "ai_conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


class ChatMessageModel(Base):
    __tablename__ = "ai_chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    conversation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ai_conversations.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )


class MemoryFactModel(Base):
    __tablename__ = "ai_memory_facts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


class SqlAlchemyConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_conversations(self, user_id: int) -> list[Conversation]:
        models = await self._session.scalars(
            select(ConversationModel)
            .where(ConversationModel.user_id == user_id)
            .order_by(ConversationModel.updated_at.desc())
        )
        return [
            Conversation(id=m.id, title=m.title, updated_at=m.updated_at)
            for m in models
        ]

    async def create_conversation(self, user_id: int, title: str) -> Conversation:
        model = ConversationModel(user_id=user_id, title=title)
        self._session.add(model)
        await self._session.flush()
        return Conversation(id=model.id, title=model.title, updated_at=model.updated_at)


class SqlAlchemyChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_message(
        self, user_id: int, conversation_id: int, role: str, content: str
    ) -> None:
        self._session.add(
            ChatMessageModel(
                user_id=user_id,
                conversation_id=conversation_id,
                role=role,
                content=content,
            )
        )
        # Bumps the conversation's `updated_at` so the sidebar list (sorted
        # by that column) surfaces the most recently active conversation
        # first, same convention as ChatGPT.
        conversation = await self._session.get(ConversationModel, conversation_id)
        if conversation is not None:
            conversation.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await self._session.flush()

    async def list_recent(
        self, user_id: int, conversation_id: int, limit: int
    ) -> list[ChatMessageRecord]:
        models = await self._session.scalars(
            select(ChatMessageModel)
            .where(
                ChatMessageModel.user_id == user_id,
                ChatMessageModel.conversation_id == conversation_id,
            )
            .order_by(ChatMessageModel.id.desc())
            .limit(limit)
        )
        records = [
            ChatMessageRecord(role=m.role, content=m.content, created_at=m.created_at)
            for m in models
        ]
        return list(reversed(records))


class SqlAlchemyMemoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_facts(self, user_id: int) -> list[MemoryFact]:
        models = await self._session.scalars(
            select(MemoryFactModel)
            .where(MemoryFactModel.user_id == user_id)
            .order_by(MemoryFactModel.id.asc())
        )
        return [MemoryFact(content=m.content) for m in models]

    async def replace_facts(self, user_id: int, facts: list[str]) -> None:
        # Replace-all rather than append: the LLM already returns the full
        # consolidated set each time (see OllamaClient.extract_memory_facts),
        # so this is where stale/contradicted facts actually disappear.
        await self._session.execute(
            delete(MemoryFactModel).where(MemoryFactModel.user_id == user_id)
        )
        for content in facts:
            self._session.add(MemoryFactModel(user_id=user_id, content=content))
        await self._session.flush()
