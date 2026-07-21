from datetime import datetime

import pytest

from src.modules.auth.application.dto import LoginRequest
from src.modules.auth.application.use_cases.get_current_user import (
    GetCurrentUserUseCase,
)
from src.modules.auth.application.use_cases.login import LoginUseCase
from src.modules.auth.domain.entities import User
from src.shared.kernel.errors import UnauthorizedError

USER = User(id=1, email="a@b.c", password_hash="hash:secret", created_at=datetime(2026, 1, 1))


class FakeUserRepository:
    def __init__(self, users: list[User]) -> None:
        self._users = users

    def get_by_email(self, email: str) -> User | None:
        return next((u for u in self._users if u.email == email), None)

    def get_by_id(self, user_id: int) -> User | None:
        return next((u for u in self._users if u.id == user_id), None)

    def add(self, email: str, password_hash: str) -> User:
        raise NotImplementedError


class FakeHasher:
    def hash(self, password: str) -> str:
        return f"hash:{password}"

    def verify(self, password: str, password_hash: str) -> bool:
        return password_hash == f"hash:{password}"


class FakeTokens:
    def issue(self, user_id: int) -> str:
        return f"token-{user_id}"

    def verify(self, token: str) -> int | None:
        return int(token.removeprefix("token-")) if token.startswith("token-") else None


def make_use_case(users: list[User] | None = None) -> LoginUseCase:
    return LoginUseCase(FakeUserRepository(users or [USER]), FakeHasher(), FakeTokens())


def test_login_returns_token_for_valid_credentials():
    response = make_use_case().execute(LoginRequest(email="a@b.c", password="secret"))
    assert response.access_token == "token-1"
    assert response.token_type == "bearer"


def test_login_rejects_wrong_password():
    with pytest.raises(UnauthorizedError):
        make_use_case().execute(LoginRequest(email="a@b.c", password="wrong"))


def test_login_rejects_unknown_email():
    with pytest.raises(UnauthorizedError):
        make_use_case().execute(LoginRequest(email="x@y.z", password="secret"))


def test_get_current_user_resolves_valid_token():
    use_case = GetCurrentUserUseCase(FakeUserRepository([USER]), FakeTokens())
    profile = use_case.execute("token-1")
    assert profile.id == 1
    assert profile.email == "a@b.c"


def test_get_current_user_rejects_invalid_token():
    use_case = GetCurrentUserUseCase(FakeUserRepository([USER]), FakeTokens())
    with pytest.raises(UnauthorizedError):
        use_case.execute("garbage")
