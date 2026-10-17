"""科目データの読取契約。開発用一覧でも所属を保存・変更しない。"""

from abc import ABC, abstractmethod
from uuid import UUID

from pydantic import BaseModel

from modules.shared.grad_checker_shared.application.unit_of_work import UnitOfWork


class SubjectListProgram(BaseModel):
    curriculum_id: UUID
    name: str
    faculty_name: str
    specialization_name: str | None
    course_name: str | None
    verification_status: str
    admission_year_from: int | None
    admission_year_to: int | None
    source_document: str
    source_pages: str


class SubjectListClassification(BaseModel):
    id: UUID
    name: str


class SubjectListOffering(BaseModel):
    term_code: str
    semester_order: int
    academic_year: int | None
    source_note: str | None


class SubjectListItem(BaseModel):
    id: UUID
    code: str
    name: str
    credits: int
    faculty_name: str
    department_name: str | None
    specialization_name: str | None
    teaching_type_label: str
    course_type: str
    classification_path: list[SubjectListClassification]
    offerings: list[SubjectListOffering]


class SubjectList(BaseModel):
    program: SubjectListProgram
    courses: list[SubjectListItem]


class SubjectListRepository(ABC):
    @abstractmethod
    def list_programs(self) -> list[SubjectListProgram]:
        """選択できる課程一覧を取得する。"""

    @abstractmethod
    def get_subject_list(self, curriculum_id: UUID) -> SubjectList:
        """指定課程の科目一覧を取得する。"""


class SubjectListUnitOfWork(UnitOfWork):
    @property
    @abstractmethod
    def subject_list(self) -> SubjectListRepository: ...


def list_subject_programs(uow: SubjectListUnitOfWork) -> list[SubjectListProgram]:
    with uow.read():
        return uow.subject_list.list_programs()


def get_subject_list(uow: SubjectListUnitOfWork, curriculum_id: UUID) -> SubjectList:
    with uow.read():
        return uow.subject_list.get_subject_list(curriculum_id)
