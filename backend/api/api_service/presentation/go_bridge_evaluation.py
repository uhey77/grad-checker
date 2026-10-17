"""本人の保存済み成績から卒業単位を判定するブリッジアダプター。"""

from fastapi import APIRouter, Request

from api.api_service.presentation.dependencies import (
    current_identity,
    database_engine,
)
from api.api_service.presentation.go_bridge_call import SessionCall, respond
from modules.requirements.grad_checker_requirements.application import (
    student_evaluation,
)
from modules.requirements.grad_checker_requirements.infrastructure.evaluation import (
    SqliteEvaluationUnitOfWork,
)

router = APIRouter(prefix="/bridge")


@router.post("/graduation-requirements")
def graduation_requirements(call: SessionCall, request: Request) -> dict[str, object]:
    def run() -> object:
        identity = current_identity(request, call.token)
        service = student_evaluation.EvaluationService(
            SqliteEvaluationUnitOfWork(database_engine(request))
        )
        return service.evaluate(identity.account.id)

    return respond(run)
