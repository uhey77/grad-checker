"""Goからユースケースを呼ぶブリッジアダプター。外部API仕様は持たない。"""

from typing import Annotated, Literal, Self
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, model_validator

from api.api_service.presentation.dependencies import subject_list_uow
from api.api_service.presentation.go_bridge_call import respond
from modules.subjects.grad_checker_subjects.public import (
    SubjectListUnitOfWork,
    get_subject_list,
    list_subject_programs,
)

router = APIRouter(prefix="/bridge")


class SubjectListCall(BaseModel):
    """ブリッジ通信の整合性検証。外部向けUUID検証・日本語応答はGoが担当。"""

    model_config = ConfigDict(extra="forbid")
    operation: Literal["list_programs", "get_subject_list"]
    curriculum_id: UUID | None = None

    @model_validator(mode="after")
    def check_operation_arguments(self) -> Self:
        if (self.operation == "get_subject_list") != (self.curriculum_id is not None):
            raise ValueError("operation and arguments do not match")
        return self


@router.post("/subject-list")
def subject_list(
    call: SubjectListCall,
    uow: Annotated[SubjectListUnitOfWork, Depends(subject_list_uow)],
) -> dict[str, object]:

    def run() -> object:
        if call.curriculum_id is None:
            return list_subject_programs(uow)
        return get_subject_list(uow, call.curriculum_id)

    return respond(run)
