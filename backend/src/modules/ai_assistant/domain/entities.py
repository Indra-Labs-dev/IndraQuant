from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ChatMessageRecord:
    role: str
    content: str
    created_at: datetime


@dataclass(frozen=True)
class MemoryFact:
    content: str


@dataclass(frozen=True)
class Conversation:
    id: int
    title: str | None
    updated_at: datetime
