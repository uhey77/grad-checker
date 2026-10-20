"""本人の判定履歴を保存・一覧・取得するブリッジアダプター。本人IDはセッションからのみ決定する。"""

from typing import Annotated, Literal, Self
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import Field, model_validator

from api.api_service.presentation.dependencies import (
    authenticate_session,
    create_check,
    current_identity,
    get_check,
    list_checks,
)
from api.api_service.presentation.go_bridge_call import WritableSessionCall, respond
from modules.accounts.grad_checker_accounts.public import AuthenticateSessionUseCase
from modules.requirements.grad_checker_requirements.public import (
    CheckPage,
    CheckRequest,
    CreateCheckUseCase,
    GetCheckUseCase,
    ListChecksUseCase,
)

router = APIRouter(prefix="/bridge")


class CheckCall(WritableSessionCall):
    operation: Literal["create", "list", "get"]
    request: CheckRequest | None = None
    page: CheckPage | None = None
    check_id: UUID | None = Field(default=None, strict=False)

    @model_validator(mode="after")
    def arguments_match(self) -> Self:
        if (self.operation == "get") != (self.check_id is not None):
            raise ValueError("check_id is required only for get")
        if (self.operation == "list") != (self.page is not None):
            raise ValueError("page is required only for list")
        return self.check_write(self.operation == "create", self.request)


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
