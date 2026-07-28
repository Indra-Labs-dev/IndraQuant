from typing import Protocol

from src.modules.auth.domain.entities import User


class UserRepository(Protocol):
    async def get_by_email(self, email: str) -> User | None: ...

    async def get_by_id(self, user_id: int) -> User | None: ...

    async def add(self, email: str, password_hash: str) -> User: ...
