"""本人成績のブリッジアダプター。本人IDはセッションからのみ決定する。"""

from typing import Annotated, Literal, Self

from fastapi import APIRouter, Depends
from pydantic import model_validator

from api.api_service.presentation.dependencies import (
    authenticate_session,
    current_identity,
    get_grades,
    save_grades,
)
from api.api_service.presentation.go_bridge_call import WritableSessionCall, respond
from modules.accounts.grad_checker_accounts.public import AuthenticateSessionUseCase
from modules.grades.grad_checker_grades.public import (
    GetGradesUseCase,
    GradeSet,
    SaveGradesUseCase,
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
    call: GradeCall,
    get_grades: Annotated[GetGradesUseCase, Depends(get_grades)],
    save_grades: Annotated[SaveGradesUseCase, Depends(save_grades)],
    auth: Annotated[AuthenticateSessionUseCase, Depends(authenticate_session)],
) -> dict[str, object]:
    def run() -> object:
        if call.operation == "save":
            identity = current_identity(auth, call.token, call.csrf)
            assert call.grade_set is not None
            return save_grades.execute(identity.account.id, call.grade_set)
        identity = current_identity(auth, call.token)
        return get_grades.execute(identity.account.id)

    return respond(run)
