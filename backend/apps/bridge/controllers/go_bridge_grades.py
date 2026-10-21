"""本人成績のブリッジアダプター。本人IDはセッションからのみ決定する。"""

from typing import Annotated

from fastapi import APIRouter, Depends

from apps.bridge.controllers.go_bridge_call import respond
from apps.bridge.dependencies import (
    authenticate_session,
    current_identity,
    get_grades,
    save_grades,
)
from apps.bridge.schemas.grades import GradeCall
from modules.accounts.public import AuthenticateSessionUseCase
from modules.grades.public import GetGradesUseCase, SaveGradesUseCase

router = APIRouter(prefix="/bridge")


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
