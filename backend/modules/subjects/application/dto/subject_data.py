"""科目マスタ投入用のモデルと型・値の制約。"""

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from modules.subjects.domain.value_objects.curriculum_verification_status import (
    VerificationStatus,
)
from modules.subjects.domain.value_objects.subject_type import SubjectType
from modules.subjects.domain.value_objects.teaching_type import TeachingType

PositiveInteger = Annotated[int, Field(strict=True, gt=0)]


NonnegativeInteger = Annotated[int, Field(strict=True, ge=0)]


NonemptyText = Annotated[str, Field(strict=True, min_length=1)]


class SeedRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AcademicProgramData(SeedRecord):
    id: UUID
    code: NonemptyText
    faculty_name: NonemptyText
    department_name: NonemptyText | None = None
    specialization_name: NonemptyText | None = None
    course_name: NonemptyText | None = None


class CurriculumData(SeedRecord):
    id: UUID
    program_id: UUID
    code: NonemptyText
    name: NonemptyText
    revision: PositiveInteger
    admission_year_from: PositiveInteger | None = None
    admission_year_to: PositiveInteger | None = None
    source_document: NonemptyText
    source_pages: NonemptyText
    verification_status: VerificationStatus


class ClassificationData(SeedRecord):
    id: UUID
    curriculum_id: UUID
    code: NonemptyText
    name: NonemptyText
    parent_id: UUID | None = None
    level: NonnegativeInteger
    display_order: NonnegativeInteger = 0


class SubjectData(SeedRecord):
    id: UUID
    code: NonemptyText
    name: NonemptyText
    credits: PositiveInteger
    offering_program_id: UUID
    teaching_type: TeachingType
    teaching_type_label: NonemptyText


class SubjectOfferingData(SeedRecord):
    course_id: UUID
    term_code: NonemptyText
    semester_order: PositiveInteger
    academic_year: PositiveInteger | None = None
    source_note: NonemptyText | None = None


class CurriculumSubjectData(SeedRecord):
    curriculum_id: UUID
    course_id: UUID
    classification_id: UUID
    course_type: SubjectType
    display_order: NonnegativeInteger = 0


class SubjectDataSeed(SeedRecord):
    academic_programs: list[AcademicProgramData]
    curricula: list[CurriculumData]
    classifications: list[ClassificationData]
    courses: list[SubjectData]
    course_offerings: list[SubjectOfferingData]
    curriculum_courses: list[CurriculumSubjectData]
