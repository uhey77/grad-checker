"""本人の保存済み成績から卒業単位を判定するブリッジアダプター。"""

from typing import Annotated

from fastapi import APIRouter, Depends

from api.api_service.presentation.dependencies import (
    auth_service,
    current_identity,
    evaluation_service,
)
from api.api_service.presentation.go_bridge_call import SessionCall, respond
from modules.accounts.grad_checker_accounts.public import AuthService
from modules.requirements.grad_checker_requirements.public import EvaluationService

router = APIRouter(prefix="/bridge")


@router.post("/dashboard")
def dashboard(
    call: SessionCall,
    auth: Annotated[AuthService, Depends(auth_service)],
    service: Annotated[EvaluationService, Depends(evaluation_service)],
) -> dict[str, object]:
    def run() -> object:
        identity = current_identity(auth, call.token)
        return service.dashboard(identity.account.id)

    return respond(run)


@router.post("/graduation-requirements")
def graduation_requirements(
    call: SessionCall,
    auth: Annotated[AuthService, Depends(auth_service)],
    service: Annotated[EvaluationService, Depends(evaluation_service)],
) -> dict[str, object]:
    def run() -> object:
        identity = current_identity(auth, call.token)
        return service.evaluate(identity.account.id)

    return respond(run)
