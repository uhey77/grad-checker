"""本人成績のブリッジアダプター。本人IDはセッションからのみ決定する。"""

from typing import Literal, Self

from fastapi import APIRouter, Request
from pydantic import model_validator

from api.api_service.presentation.dependencies import (
    SessionDependency,
    current_identity,
)
from api.api_service.presentation.go_bridge_call import WritableSessionCall, respond
from modules.grades.grad_checker_grades.application.grades import (
    GradeService,
    GradeSet,
)
from modules.grades.grad_checker_grades.infrastructure.grades import (
    SqliteGradeRepository,
)

router = APIRouter(prefix="/bridge")


class GradeCall(WritableSessionCall):
    operation: Literal["get", "save"]
    grade_set: GradeSet | None = None

    @model_validator(mode="after")
    def arguments_match(self) -> Self:
        return self.check_write(self.operation == "save", self.grade_set)


@router.post("/grades")
def grades(
    call: GradeCall, request: Request, session: SessionDependency
) -> dict[str, object]:
    def run() -> object:
        service = GradeService(SqliteGradeRepository(session))
        if call.operation == "save":
            identity = current_identity(request, call.token, call.csrf)
            assert call.grade_set is not None
            return service.save_grades(identity.account.id, call.grade_set)
        identity = current_identity(request, call.token)
        return service.get_grades(identity.account.id)

    return respond(run)
