"""本人の保存済み成績から卒業単位を判定するブリッジアダプター。"""

from fastapi import APIRouter, Request

from api.api_service.presentation.dependencies import (
    SessionDependency,
    current_identity,
)
from api.api_service.presentation.go_bridge_call import SessionCall, respond
from modules.requirements.grad_checker_requirements.application import (
    student_evaluation,
)
from modules.requirements.grad_checker_requirements.infrastructure.evaluation import (
    SqliteEvaluationRepository,
)

router = APIRouter(prefix="/bridge")


@router.post("/graduation-requirements")
def graduation_requirements(
    call: SessionCall, request: Request, session: SessionDependency
) -> dict[str, object]:
    def run() -> object:
        identity = current_identity(request, call.token)
        service = student_evaluation.EvaluationService(
            SqliteEvaluationRepository(session)
        )
        return service.evaluate(identity.account.id)

    return respond(run)
