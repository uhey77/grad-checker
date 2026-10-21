"""本人の保存済み成績から卒業単位を判定するブリッジアダプター。"""

from typing import Annotated

from fastapi import APIRouter, Depends

from apps.bridge.controllers.go_bridge_call import respond
from apps.bridge.dependencies import (
    authenticate_session,
    current_identity,
    evaluate_graduation,
    get_dashboard,
)
from apps.bridge.schemas.call import SessionCall
from modules.accounts.public import AuthenticateSessionUseCase
from modules.requirements.public import EvaluateGraduationUseCase, GetDashboardUseCase

router = APIRouter(prefix="/bridge")


@router.post("/dashboard")
def dashboard(
    call: SessionCall,
    auth: Annotated[AuthenticateSessionUseCase, Depends(authenticate_session)],
    service: Annotated[GetDashboardUseCase, Depends(get_dashboard)],
) -> dict[str, object]:
    def run() -> object:
        identity = current_identity(auth, call.token)
        return service.execute(identity.account.id)

    return respond(run)


@router.post("/graduation-requirements")
def graduation_requirements(
    call: SessionCall,
    auth: Annotated[AuthenticateSessionUseCase, Depends(authenticate_session)],
    service: Annotated[EvaluateGraduationUseCase, Depends(evaluate_graduation)],
) -> dict[str, object]:
    def run() -> object:
        identity = current_identity(auth, call.token)
        return service.execute(identity.account.id)

    return respond(run)
