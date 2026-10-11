"""Goからユースケースを呼ぶ内部通信アダプター。外部API仕様は持たない。"""

import logging
from typing import Literal, Self
from uuid import UUID

from fastapi import APIRouter
from grad_checker_subjects.application.errors.subject_list import (
    SubjectListIntegrityError,
    SubjectListNotFoundError,
    SubjectListUnavailableError,
)
from grad_checker_subjects.application.subject_list import (
    get_subject_list,
    list_subject_programs,
)
from grad_checker_subjects.infrastructure.subject_list import (
    SqliteSubjectListRepository,
)
from pydantic import BaseModel, ConfigDict, model_validator

from api_service.presentation.dependencies import SessionDependency

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/internal")


class SubjectListCall(BaseModel):
    """内部通信の整合性検証。外部向けUUID検証・日本語応答はGoが担当。"""

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
    try:
        if call.curriculum_id is None:
            result = list_subject_programs(repository)
        else:
            result = get_subject_list(repository, call.curriculum_id)
        return {"data": result}
    except SubjectListNotFoundError:
        return {"error": {"code": "curriculum_not_found"}}
    except SubjectListIntegrityError:
        return {"error": {"code": "classification_inconsistent"}}
    except SubjectListUnavailableError:
        return {"error": {"code": "subject_list_unavailable"}}
    except Exception:
        logger.exception("Unexpected subject list failure")
        return {"error": {"code": "internal_error"}}
