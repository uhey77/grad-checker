"""本人成績のブリッジアダプター。本人IDはセッションからのみ決定する。"""

from typing import Annotated, Literal, Self

from fastapi import APIRouter, Depends
from pydantic import model_validator

from api.api_service.presentation.dependencies import (
    auth_service,
    current_identity,
    grade_service,
)
from api.api_service.presentation.go_bridge_call import WritableSessionCall, respond
from modules.accounts.grad_checker_accounts.public import AuthService
from modules.grades.grad_checker_grades.public import GradeService, GradeSet

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
    auth: Annotated[AuthService, Depends(auth_service)],
    service: Annotated[GradeService, Depends(grade_service)],
) -> dict[str, object]:
    def run() -> object:
        if call.operation == "save":
            identity = current_identity(auth, call.token, call.csrf)
            assert call.grade_set is not None
            return service.save_grades(identity.account.id, call.grade_set)
        identity = current_identity(auth, call.token)
        return service.get_grades(identity.account.id)

    return respond(run)
