from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator


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
