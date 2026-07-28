from fastapi import APIRouter, Depends

from src.composition_root import get_chat_use_case, get_current_user
from src.modules.ai_assistant.application.use_cases.chat import (
    ChatRequest,
    ChatResponse,
    ChatUseCase,
)
from src.modules.auth.application.dto import UserProfile

router = APIRouter(prefix="/assistant", tags=["ai-assistant"])


@router.post("/chat")
async def chat(
    request: ChatRequest,
    _: UserProfile = Depends(get_current_user),
    use_case: ChatUseCase = Depends(get_chat_use_case),
) -> ChatResponse:
    return await use_case.execute(request)
