"""本人の判定履歴を保存・取得するブリッジアダプター。本人IDはセッションからのみ決定する。"""

from typing import Literal, Self
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import Field, model_validator

from api.api_service.presentation.dependencies import (
    current_identity,
    database_engine,
)
from api.api_service.presentation.go_bridge_call import WritableSessionCall, respond
from modules.requirements.grad_checker_requirements.application import check_results
from modules.requirements.grad_checker_requirements.infrastructure import (
    check_results as check_storage,
)

router = APIRouter(prefix="/bridge")


class CheckCall(WritableSessionCall):
    operation: Literal["create", "get"]
    request: check_results.CheckRequest | None = None
    check_id: UUID | None = Field(default=None, strict=False)

    @model_validator(mode="after")
    def arguments_match(self) -> Self:
        creates = self.operation == "create"
        if creates != (self.check_id is None):
            raise ValueError("check_id is required only for get")
        return self.check_write(creates, self.request)


@router.post("/checks")
def checks(call: CheckCall, request: Request) -> dict[str, object]:
    def run() -> object:
        service = check_results.CheckService(
            check_storage.SqliteCheckUnitOfWork(database_engine(request))
        )
        if call.operation == "create":
            identity = current_identity(request, call.token, call.csrf)
            assert call.request is not None
            return service.create_check(identity.account.id, call.request)
        identity = current_identity(request, call.token)
        assert call.check_id is not None
        return service.get_check(identity.account.id, call.check_id)

    return respond(run)
