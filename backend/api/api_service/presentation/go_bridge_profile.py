"""本人情報のブリッジアダプター。本人IDはセッションからのみ決定する。"""

from typing import Literal, Self

from fastapi import APIRouter, Request
from pydantic import model_validator

from api.api_service.presentation.dependencies import (
    current_identity,
    database_engine,
)
from api.api_service.presentation.go_bridge_call import WritableSessionCall, respond
from modules.accounts.grad_checker_accounts.application.profile import (
    ProfileService,
    ProgramSelection,
)
from modules.accounts.grad_checker_accounts.infrastructure.profile import (
    SqliteProfileUnitOfWork,
)

router = APIRouter(prefix="/bridge")


class ProfileCall(WritableSessionCall):
    operation: Literal["programs", "me", "save_program"]
    selection: ProgramSelection | None = None

    @model_validator(mode="after")
    def arguments_match(self) -> Self:
        return self.check_write(self.operation == "save_program", self.selection)


@router.post("/profile")
def profile(call: ProfileCall, request: Request) -> dict[str, object]:
    def run() -> object:
        service = ProfileService(SqliteProfileUnitOfWork(database_engine(request)))
        if call.operation == "save_program":
            identity = current_identity(request, call.token, call.csrf)
            assert call.selection is not None
            return {
                "profile": service.save_program(identity.account.id, call.selection)
            }
        identity = current_identity(request, call.token)
        if call.operation == "programs":
            return {"programs": service.list_programs()}
        return {"profile": service.get_profile(identity.account.id)}

    return respond(run)
