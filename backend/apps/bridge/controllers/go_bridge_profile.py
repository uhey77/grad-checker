"""本人情報のブリッジアダプター。本人IDはセッションからのみ決定する。"""

from typing import Annotated

from fastapi import APIRouter, Depends

from apps.bridge.controllers.go_bridge_call import respond
from apps.bridge.dependencies import (
    authenticate_session,
    current_identity,
    get_profile,
    list_programs,
    save_program,
)
from apps.bridge.schemas.profile import ProfileCall
from modules.accounts.public import (
    AuthenticateSessionUseCase,
    GetProfileUseCase,
    ListProgramsUseCase,
    SaveProgramUseCase,
)

router = APIRouter(prefix="/bridge")


@router.post("/profile")
def profile(
    call: ProfileCall,
    list_programs: Annotated[ListProgramsUseCase, Depends(list_programs)],
    get_profile: Annotated[GetProfileUseCase, Depends(get_profile)],
    save_program: Annotated[SaveProgramUseCase, Depends(save_program)],
    auth: Annotated[AuthenticateSessionUseCase, Depends(authenticate_session)],
) -> dict[str, object]:
    def run() -> object:
        if call.operation == "save_program":
            identity = current_identity(auth, call.token, call.csrf)
            assert call.selection is not None
            return {
                "profile": save_program.execute(identity.account.id, call.selection)
            }
        identity = current_identity(auth, call.token)
        if call.operation == "programs":
            return {"programs": list_programs.execute()}
        return {"profile": get_profile.execute(identity.account.id)}

    return respond(run)
