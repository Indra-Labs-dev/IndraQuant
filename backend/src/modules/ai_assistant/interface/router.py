from fastapi import APIRouter, Depends

from src.composition_root import (
    get_chat_history_use_case,
    get_chat_use_case,
    get_clear_memory_use_case,
    get_current_user,
    get_memory_use_case,
)
from src.modules.ai_assistant.application.use_cases.chat import (
    ChatRequest,
    ChatResponse,
    ChatUseCase,
)
from src.modules.ai_assistant.application.use_cases.get_chat_history import (
    ChatHistoryResponse,
    GetChatHistoryUseCase,
)
from src.modules.ai_assistant.application.use_cases.manage_memory import (
    ClearMemoryUseCase,
    GetMemoryUseCase,
    MemoryResponse,
)
from src.modules.auth.application.dto import UserProfile

router = APIRouter(prefix="/assistant", tags=["ai-assistant"])


@router.post("/chat")
async def chat(
    request: ChatRequest,
    user: UserProfile = Depends(get_current_user),
    use_case: ChatUseCase = Depends(get_chat_use_case),
) -> ChatResponse:
    return await use_case.execute(user.id, request)


@router.get("/history")
async def history(
    user: UserProfile = Depends(get_current_user),
    use_case: GetChatHistoryUseCase = Depends(get_chat_history_use_case),
) -> ChatHistoryResponse:
    return await use_case.execute(user.id)


@router.get("/memory")
async def memory(
    user: UserProfile = Depends(get_current_user),
    use_case: GetMemoryUseCase = Depends(get_memory_use_case),
) -> MemoryResponse:
    return await use_case.execute(user.id)


@router.delete("/memory")
async def clear_memory(
    user: UserProfile = Depends(get_current_user),
    use_case: ClearMemoryUseCase = Depends(get_clear_memory_use_case),
) -> MemoryResponse:
    return await use_case.execute(user.id)
