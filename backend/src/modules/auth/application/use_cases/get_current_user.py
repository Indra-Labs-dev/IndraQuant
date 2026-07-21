from src.modules.auth.application.dto import UserProfile
from src.modules.auth.application.ports import TokenProvider
from src.modules.auth.domain.repositories import UserRepository
from src.shared.kernel.errors import UnauthorizedError


class GetCurrentUserUseCase:
    def __init__(self, users: UserRepository, tokens: TokenProvider) -> None:
        self._users = users
        self._tokens = tokens

    def execute(self, token: str) -> UserProfile:
        user_id = self._tokens.verify(token)
        user = self._users.get_by_id(user_id) if user_id is not None else None
        if user is None:
            raise UnauthorizedError("invalid_token", "Session invalide ou expirée.")
        return UserProfile(id=user.id, email=user.email)
