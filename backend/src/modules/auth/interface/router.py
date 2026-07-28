from fastapi import APIRouter, Depends

from src.composition_root import get_current_user, get_login_use_case
from src.modules.auth.application.dto import LoginRequest, LoginResponse, UserProfile
from src.modules.auth.application.use_cases.login import LoginUseCase

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(
    request: LoginRequest,
    use_case: LoginUseCase = Depends(get_login_use_case),
) -> LoginResponse:
    return await use_case.execute(request)


@router.post("/logout")
def logout(_: UserProfile = Depends(get_current_user)) -> dict:
    # Stateless JWT (ADR-008): the client discards the token.
    return {"status": "ok"}


@router.get("/me")
def me(user: UserProfile = Depends(get_current_user)) -> UserProfile:
    return user
