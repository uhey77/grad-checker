"""本人の所属と選択可能な課程の入出力。"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from modules.requirements.public import CompletionPolicyData

type VerificationStatus = Literal["unverified", "verified"]


class ProgramOption(BaseModel):
    completion_policy: CompletionPolicyData | None = None
    program_id: str
    curriculum_id: str
    faculty_name: str
    department_name: str | None
    specialization_name: str | None
    course_name: str | None
    curriculum_name: str
    revision: int
    verification_status: VerificationStatus
    admission_year_from: int | None
    admission_year_to: int | None
    source_document: str
    source_pages: str


class Profile(BaseModel):
    student_id: str
    login_name: str
    program_id: str | None
    curriculum_id: str | None
    data_revision: int


class ProgramSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    program_id: str = Field(min_length=1, max_length=36)
    curriculum_id: str = Field(min_length=1, max_length=36)
    expected_revision: int = Field(ge=0, le=9007199254740990)
