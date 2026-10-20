"""本人の判定履歴を保存・一覧・取得するブリッジアダプター。本人IDはセッションからのみ決定する。"""

from typing import Annotated

from fastapi import APIRouter, Depends

from apps.bridge.controllers.go_bridge_call import respond
from apps.bridge.dependencies import (
    authenticate_session,
    create_check,
    current_identity,
    get_check,
    list_checks,
)
from apps.bridge.schemas.checks import CheckCall
from modules.accounts.public import AuthenticateSessionUseCase
from modules.requirements.public import (
    CreateCheckUseCase,
    GetCheckUseCase,
    ListChecksUseCase,
)

router = APIRouter(prefix="/bridge")


@router.post("/checks")
def checks(
    call: CheckCall,
    create_check: Annotated[CreateCheckUseCase, Depends(create_check)],
    get_check: Annotated[GetCheckUseCase, Depends(get_check)],
    list_checks: Annotated[ListChecksUseCase, Depends(list_checks)],
    auth: Annotated[AuthenticateSessionUseCase, Depends(authenticate_session)],
) -> dict[str, object]:
    def run() -> object:
        if call.operation == "create":
            identity = current_identity(auth, call.token, call.csrf)
            assert call.request is not None
            return create_check.execute(identity.account.id, call.request)
        identity = current_identity(auth, call.token)
        if call.operation == "list":
            assert call.page is not None
            return list_checks.execute(identity.account.id, call.page)
        assert call.check_id is not None
        return get_check.execute(identity.account.id, call.check_id)

    return respond(run)
