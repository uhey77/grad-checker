"""本人課程から見た既知科目と分類の読取契約。成績や所属は変更しない。"""

from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from modules.shared.grad_checker_shared.application.unit_of_work import UnitOfWork
from modules.subjects.grad_checker_subjects.domain.subject_type import SubjectType

from ..domain.curriculum_verification_status import (
    VerificationStatus,
)

type TermCode = Literal["first", "second"]


class CatalogCurriculum(BaseModel):
    curriculum_id: str
    name: str
    verification_status: VerificationStatus
    admission_year_from: int | None
    admission_year_to: int | None
    source_document: str
    source_pages: str


class CatalogCategory(BaseModel):
    id: str
    code: str
    name: str
    parent_id: str | None
    level: int
    display_order: int


class CatalogClassification(BaseModel):
    id: str
    name: str


class CatalogPlacement(BaseModel):
    """本人課程での分類・種別。科目表にない科目には推測で設定しない。"""

    classification_path: list[CatalogClassification]
    course_type: SubjectType


class CatalogOffering(BaseModel):
    term_code: str
    semester_order: int
    academic_year: int | None
    source_note: str | None


class CatalogCourse(BaseModel):
    course_id: str
    code: str
    name: str
    credits: int
    offering_faculty_name: str
    offering_department_name: str | None
    offering_specialization_name: str | None
    teaching_type: str
    teaching_type_label: str
    offerings: list[CatalogOffering]
    placement: CatalogPlacement | None


class CourseCatalog(BaseModel):
    curriculum: CatalogCurriculum
    categories: list[CatalogCategory]
    courses: list[CatalogCourse]


class CourseList(BaseModel):
    curriculum: CatalogCurriculum
    courses: list[CatalogCourse]


class CategoryList(BaseModel):
    curriculum: CatalogCurriculum
    categories: list[CatalogCategory]


class CourseFilters(BaseModel):
    """複数指定はAND。学期は科目の開講学期で、本人の履修学期ではない。"""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    category_id: str | None = Field(default=None, min_length=36, max_length=36)
    faculty: str | None = Field(default=None, min_length=1, max_length=100)
    department: str | None = Field(default=None, min_length=1, max_length=100)
    semester: TermCode | None = None
    q: str | None = Field(default=None, min_length=1, max_length=100)


class CourseCatalogRepository(ABC):
    @abstractmethod
    def get_catalog(self, curriculum_id: str) -> CourseCatalog: ...


def matches(course: CatalogCourse, filters: CourseFilters) -> bool:
    if filters.category_id is not None and (
        course.placement is None
        or all(
            c.id != filters.category_id for c in course.placement.classification_path
        )
    ):
        return False
    if filters.faculty is not None and course.offering_faculty_name != filters.faculty:
        return False
    if (
        filters.department is not None
        and course.offering_department_name != filters.department
    ):
        return False
    if filters.semester is not None and all(
        offering.term_code != filters.semester for offering in course.offerings
    ):
        return False
    if filters.q is not None:
        keyword = filters.q.casefold()
        return keyword in course.name.casefold() or keyword in course.code.casefold()
    return True


class CourseCatalogUnitOfWork(UnitOfWork):
    @property
    @abstractmethod
    def catalog(self) -> CourseCatalogRepository: ...
