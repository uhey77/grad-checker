"""本人情報のブリッジアダプター。本人IDはセッションからのみ決定する。"""

from typing import Annotated, Literal, Self

from fastapi import APIRouter, Depends
from pydantic import model_validator

from api.api_service.presentation.dependencies import (
    auth_service,
    current_identity,
    profile_service,
)
from api.api_service.presentation.go_bridge_call import WritableSessionCall, respond
from modules.accounts.grad_checker_accounts.public import (
    AuthService,
    ProfileService,
    ProgramSelection,
)

router = APIRouter(prefix="/bridge")


class ProfileCall(WritableSessionCall):
    operation: Literal["programs", "me", "save_program"]
    selection: ProgramSelection | None = None

    @model_validator(mode="after")
    def arguments_match(self) -> Self:
        return self.check_write(self.operation == "save_program", self.selection)


@router.post("/profile")
def profile(
    call: ProfileCall,
    auth: Annotated[AuthService, Depends(auth_service)],
    service: Annotated[ProfileService, Depends(profile_service)],
) -> dict[str, object]:
    def run() -> object:
        if call.operation == "save_program":
            identity = current_identity(auth, call.token, call.csrf)
            assert call.selection is not None
            return {
                "profile": service.save_program(identity.account.id, call.selection)
            }
        identity = current_identity(auth, call.token)
        if call.operation == "programs":
            return {"programs": service.list_programs()}
        return {"profile": service.get_profile(identity.account.id)}

    return respond(run)
