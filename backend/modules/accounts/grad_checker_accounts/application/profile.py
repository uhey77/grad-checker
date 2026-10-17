"""本人の所属とカリキュラムの取得・保存契約。"""

from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from modules.accounts.grad_checker_accounts.application.errors.profile import (
    ProfileError,
)
from modules.shared.grad_checker_shared.application.unit_of_work import UnitOfWork

type VerificationStatus = Literal["unverified", "verified"]


class ProgramOption(BaseModel):
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


class ProfileRepository(Protocol):
    def list_programs(self) -> list[ProgramOption]: ...
    def get_profile(self, student_id: str) -> Profile: ...
    def save_program(self, student_id: str, selection: ProgramSelection) -> Profile: ...


class ProfileUnitOfWork(UnitOfWork, Protocol):
    @property
    def profiles(self) -> ProfileRepository: ...


class ProfileService:
    def __init__(self, uow: ProfileUnitOfWork) -> None:
        self.uow = uow

    def list_programs(self) -> list[ProgramOption]:
        with self.uow.read():
            return self.uow.profiles.list_programs()

    def get_profile(self, student_id: str) -> Profile:
        with self.uow.read():
            return self.uow.profiles.get_profile(student_id)

    def selected_curriculum(self, student_id: str) -> str:
        """本人課程を前提とする処理のため、所属未設定を業務エラーにする。"""
        curriculum_id = self.get_profile(student_id).curriculum_id
        if curriculum_id is None:
            raise ProfileError("program_not_selected")
        return curriculum_id

    def save_program(self, student_id: str, selection: ProgramSelection) -> Profile:
        # 組合せの検証と版付き更新を、同じ書込みロックの下で行う。
        with self.uow.write():
            return self.uow.profiles.save_program(student_id, selection)
