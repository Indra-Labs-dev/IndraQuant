from src.modules.auth.application.dto import LoginRequest, LoginResponse
from src.modules.auth.application.ports import PasswordHasher, TokenProvider
from src.modules.auth.domain.repositories import UserRepository
from src.shared.kernel.errors import UnauthorizedError


class LoginUseCase:
    def __init__(
        self,
        users: UserRepository,
        hasher: PasswordHasher,
        tokens: TokenProvider,
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._tokens = tokens

    def execute(self, request: LoginRequest) -> LoginResponse:
        user = self._users.get_by_email(request.email)
        if user is None or not self._hasher.verify(
            request.password, user.password_hash
        ):
            raise UnauthorizedError(
                "invalid_credentials", "Email ou mot de passe incorrect."
            )
        return LoginResponse(access_token=self._tokens.issue(user.id))
