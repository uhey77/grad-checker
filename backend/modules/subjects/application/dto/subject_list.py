"""開発用科目一覧と選択可能な課程の入出力。"""

from uuid import UUID

from pydantic import BaseModel


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
