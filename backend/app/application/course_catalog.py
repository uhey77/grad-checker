"""科目データの読取契約。開発用一覧でも所属を保存・変更しない。"""

from abc import ABC, abstractmethod
from uuid import UUID

from pydantic import BaseModel


class CatalogProgram(BaseModel):
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


class CatalogClassification(BaseModel):
    id: UUID
    name: str


class CatalogOffering(BaseModel):
    term_code: str
    semester_order: int
    academic_year: int | None
    source_note: str | None


class CatalogCourse(BaseModel):
    id: UUID
    code: str
    name: str
    credits: int
    faculty_name: str
    department_name: str | None
    specialization_name: str | None
    teaching_type_label: str
    course_type: str
    classification_path: list[CatalogClassification]
    offerings: list[CatalogOffering]


class CourseCatalog(BaseModel):
    program: CatalogProgram
    courses: list[CatalogCourse]


class CatalogRepository(ABC):
    @abstractmethod
    def list_programs(self) -> list[CatalogProgram]:
        """選択できる課程一覧を取得する。"""

    @abstractmethod
    def get_catalog(self, curriculum_id: UUID) -> CourseCatalog:
        """指定課程の科目一覧を取得する。"""


def list_catalog_programs(repository: CatalogRepository) -> list[CatalogProgram]:
    return repository.list_programs()


def get_course_catalog(
    repository: CatalogRepository, curriculum_id: UUID
) -> CourseCatalog:
    return repository.get_catalog(curriculum_id)
