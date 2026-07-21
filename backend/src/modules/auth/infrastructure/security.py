from datetime import datetime, timedelta, timezone

import bcrypt
import jwt


class BcryptPasswordHasher:
    def hash(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify(self, password: str, password_hash: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode(), password_hash.encode())
        except ValueError:
            return False


class JwtTokenProvider:
    def __init__(self, secret: str, expires_minutes: int) -> None:
        self._secret = secret
        self._expires_minutes = expires_minutes

    def issue(self, user_id: int) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "iat": now,
            "exp": now + timedelta(minutes=self._expires_minutes),
        }
        return jwt.encode(payload, self._secret, algorithm="HS256")

    def verify(self, token: str) -> int | None:
        try:
            payload = jwt.decode(token, self._secret, algorithms=["HS256"])
            return int(payload["sub"])
        except (jwt.InvalidTokenError, KeyError, ValueError):
            return None
