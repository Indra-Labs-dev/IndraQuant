from fastapi import APIRouter, Depends

from src.composition_root import (
    get_current_user,
    get_manage_sessions_use_case,
    paper_trading_runner,
)
from src.modules.auth.application.dto import UserProfile
from src.modules.paper_trading.application.dto import (
    CreateSessionRequest,
    SessionDetail,
    SessionsResponse,
    SessionSummary,
)
from src.modules.paper_trading.application.use_cases.manage_sessions import (
    ManageSessionsUseCase,
)

router = APIRouter(prefix="/paper-trading/sessions", tags=["paper-trading"])


@router.post("")
def create_session(
    request: CreateSessionRequest,
    _: UserProfile = Depends(get_current_user),
    use_case: ManageSessionsUseCase = Depends(get_manage_sessions_use_case),
) -> SessionSummary:
    summary = use_case.create(request)
    paper_trading_runner.start(summary.id, summary.timeframe)
    return summary


@router.get("")
def list_sessions(
    _: UserProfile = Depends(get_current_user),
    use_case: ManageSessionsUseCase = Depends(get_manage_sessions_use_case),
) -> SessionsResponse:
    return use_case.list_sessions()


@router.get("/{session_id}")
def session_detail(
    session_id: int,
    _: UserProfile = Depends(get_current_user),
    use_case: ManageSessionsUseCase = Depends(get_manage_sessions_use_case),
) -> SessionDetail:
    return use_case.detail(session_id)


@router.post("/{session_id}/stop")
def stop_session(
    session_id: int,
    _: UserProfile = Depends(get_current_user),
    use_case: ManageSessionsUseCase = Depends(get_manage_sessions_use_case),
) -> SessionSummary:
    summary = use_case.stop(session_id)
    paper_trading_runner.stop(session_id)
    return summary
