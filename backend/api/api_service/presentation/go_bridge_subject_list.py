"""Goからユースケースを呼ぶブリッジアダプター。外部API仕様は持たない。"""

from typing import Literal, Self
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, model_validator

from api.api_service.presentation.dependencies import SessionDependency
from api.api_service.presentation.go_bridge_call import respond
from modules.subjects.grad_checker_subjects.application.subject_list import (
    get_subject_list,
    list_subject_programs,
)
from modules.subjects.grad_checker_subjects.infrastructure.subject_list import (
    SqliteSubjectListRepository,
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
    call: SubjectListCall, session: SessionDependency
) -> dict[str, object]:
    repository = SqliteSubjectListRepository(session)

    def run() -> object:
        if call.curriculum_id is None:
            return list_subject_programs(repository)
        return get_subject_list(repository, call.curriculum_id)

    return respond(run)
