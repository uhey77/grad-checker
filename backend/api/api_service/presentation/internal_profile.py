"""本人情報の内部アダプター。本人IDはセッションからのみ決定する。"""

import secrets
from typing import Literal, Self

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator

from api.api_service.presentation.dependencies import SessionDependency, auth_service
from modules.accounts.grad_checker_accounts.application.errors.auth import AuthError
from modules.accounts.grad_checker_accounts.application.errors.profile import (
    ProfileError,
)
from modules.accounts.grad_checker_accounts.application.profile import (
    ProfileService,
    ProgramSelection,
)
from modules.accounts.grad_checker_accounts.infrastructure.profile import (
    SqliteProfileRepository,
)

router = APIRouter(prefix="/internal")


class ProfileCall(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    operation: Literal["programs", "me", "save_program"]
    token: str = Field(min_length=43, max_length=43)
    csrf: str = Field(default="", max_length=64)
    selection: ProgramSelection | None = None

    @model_validator(mode="after")
    def arguments_match(self) -> Self:
        if self.operation == "save_program":
            if self.selection is None or len(self.csrf) != 64:
                raise ValueError("selection and csrf required")
        elif self.selection is not None or self.csrf:
            raise ValueError("unexpected write arguments")
        return self


@router.post("/profile")
def profile(
    call: ProfileCall, request: Request, session: SessionDependency
) -> dict[str, object]:
    try:
        identity = auth_service(request, session).session(call.token)
        service = ProfileService(SqliteProfileRepository(session))
        if call.operation == "programs":
            return {"data": {"programs": service.list_programs()}}
        if call.operation == "me":
            return {"data": {"profile": service.get_profile(identity.account.id)}}
        if not secrets.compare_digest(identity.csrf_token, call.csrf):
            raise AuthError("invalid_csrf")
        assert call.selection is not None
        return {
            "data": {
                "profile": service.save_program(identity.account.id, call.selection)
            }
        }
    except (AuthError, ProfileError) as error:
        return {"error": {"code": error.code}}
