"""本人の所属とカリキュラムの取得・保存契約。"""

from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from modules.requirements.grad_checker_requirements.public import CompletionPolicyData
from modules.shared.grad_checker_shared.application.unit_of_work import UnitOfWork

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


class ProfileRepository(ABC):
    @abstractmethod
    def list_programs(self) -> list[ProgramOption]: ...

    @abstractmethod
    def get_profile(self, student_id: str) -> Profile: ...

    @abstractmethod
    def save_program(self, student_id: str, selection: ProgramSelection) -> Profile: ...


class ProfileUnitOfWork(UnitOfWork):
    @property
    @abstractmethod
    def profiles(self) -> ProfileRepository: ...
