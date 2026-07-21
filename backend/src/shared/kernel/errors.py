class AppError(Exception):
    """Base error mapped to the uniform API error format (docs/10)."""

    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


class NotFoundError(AppError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message, http_status=404)


class UnauthorizedError(AppError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message, http_status=401)
