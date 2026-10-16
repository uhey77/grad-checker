"""本人成績の内部アダプター。本人IDはセッションからのみ決定する。"""

import secrets
from typing import Literal, Self

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator

from api.api_service.presentation.dependencies import SessionDependency, auth_service
from modules.accounts.grad_checker_accounts.application.errors.auth import AuthError
from modules.grades.grad_checker_grades.application.errors.grades import GradeError
from modules.grades.grad_checker_grades.application.grades import (
    GradeService,
    GradeSet,
)
from modules.grades.grad_checker_grades.infrastructure.grades import (
    SqliteGradeRepository,
)

router = APIRouter(prefix="/internal")


class GradeCall(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    operation: Literal["get", "save"]
    token: str = Field(min_length=43, max_length=43)
    csrf: str = Field(default="", max_length=64)
    grade_set: GradeSet | None = None

    @model_validator(mode="after")
    def arguments_match(self) -> Self:
        if self.operation == "save":
            if self.grade_set is None or len(self.csrf) != 64:
                raise ValueError("grade_set and csrf required")
        elif self.grade_set is not None or self.csrf:
            raise ValueError("unexpected write arguments")
        return self


@router.post("/grades")
def grades(
    call: GradeCall, request: Request, session: SessionDependency
) -> dict[str, object]:
    try:
        identity = auth_service(request, session).session(call.token)
        service = GradeService(SqliteGradeRepository(session))
        if call.operation == "get":
            return {"data": service.get_grades(identity.account.id)}
        if not secrets.compare_digest(identity.csrf_token, call.csrf):
            raise AuthError("invalid_csrf")
        assert call.grade_set is not None
        return {"data": service.save_grades(identity.account.id, call.grade_set)}
    except (AuthError, GradeError) as error:
        return {"error": {"code": error.code}}
