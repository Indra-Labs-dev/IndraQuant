from typing import Protocol


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, password_hash: str) -> bool: ...


class TokenProvider(Protocol):
    def issue(self, user_id: int) -> str: ...

    def verify(self, token: str) -> int | None:
        """Returns the user id, or None if the token is invalid/expired."""
        ...
