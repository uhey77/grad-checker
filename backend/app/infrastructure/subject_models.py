"""SQLModelの課程・科目テーブル。業務層の入力契約とは分離する。"""

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
    UniqueConstraint,
    text,
)
from sqlmodel import Field, SQLModel


def integer_check(
    column: str, minimum: int = 0, nullable: bool = False
) -> CheckConstraint:
    expression = f"typeof({column}) = 'integer' AND {column} >= {minimum}"
    if nullable:
        expression = f"{column} IS NULL OR ({expression})"
    return CheckConstraint(expression)


def text_check(column: str, nullable: bool = False) -> CheckConstraint:
    expression = f"length(trim({column})) > 0"
    if nullable:
        expression = f"{column} IS NULL OR ({expression})"
    return CheckConstraint(expression)


class AcademicProgram(SQLModel, table=True):
    __tablename__ = "academic_programs"
    __table_args__ = (
        UniqueConstraint("code"),
        text_check("code"),
        text_check("faculty_name"),
        text_check("department_name", True),
        text_check("specialization_name", True),
        text_check("course_name", True),
    )
    id: str = Field(primary_key=True)
    code: str
    faculty_name: str
    department_name: str | None = None
    specialization_name: str | None = None
    course_name: str | None = None


class Curriculum(SQLModel, table=True):
    __tablename__ = "curricula"
    __table_args__ = (
        UniqueConstraint("code"),
        text_check("code"),
        text_check("name"),
        text_check("source_document"),
        text_check("source_pages"),
        integer_check("revision", 1),
        integer_check("admission_year_from", 1, True),
        integer_check("admission_year_to", 1, True),
        CheckConstraint(
            "admission_year_from IS NULL OR admission_year_to IS NULL "
            "OR admission_year_from <= admission_year_to"
        ),
        CheckConstraint("verification_status IN ('unverified', 'verified')"),
        CheckConstraint(
            "verification_status != 'verified' OR admission_year_from IS NOT NULL"
        ),
    )
    id: str = Field(primary_key=True)
    program_id: str = Field(foreign_key="academic_programs.id", ondelete="RESTRICT")
    code: str
    name: str
    revision: int
    admission_year_from: int | None = None
    admission_year_to: int | None = None
    source_document: str
    source_pages: str
    verification_status: str


class Classification(SQLModel, table=True):
    __tablename__ = "classifications"
    __table_args__ = (
        UniqueConstraint("curriculum_id", "code"),
        UniqueConstraint("curriculum_id", "id"),
        ForeignKeyConstraint(
            ["curriculum_id", "parent_id"],
            ["classifications.curriculum_id", "classifications.id"],
            ondelete="RESTRICT",
        ),
        text_check("code"),
        text_check("name"),
        integer_check("level"),
        integer_check("display_order"),
        CheckConstraint("parent_id IS NULL OR parent_id != id"),
        CheckConstraint("parent_id IS NOT NULL OR level = 0"),
    )
    id: str = Field(primary_key=True)
    curriculum_id: str = Field(foreign_key="curricula.id", ondelete="RESTRICT")
    code: str
    name: str
    parent_id: str | None = None
    level: int
    display_order: int = 0


class Subject(SQLModel, table=True):
    __tablename__ = "courses"
    __table_args__ = (
        UniqueConstraint("code"),
        text_check("code"),
        text_check("name"),
        integer_check("credits", 1),
        text_check("teaching_type_label"),
        CheckConstraint(
            "teaching_type IN "
            "('lecture', 'exercise', 'practice', 'experiment', 'other')"
        ),
    )
    id: str = Field(primary_key=True)
    code: str
    name: str
    credits: int
    offering_program_id: str = Field(
        foreign_key="academic_programs.id", ondelete="RESTRICT"
    )
    teaching_type: str
    teaching_type_label: str


class SubjectOffering(SQLModel, table=True):
    __tablename__ = "course_offerings"
    __table_args__ = (
        # NULLを含む通常のUNIQUEは重複を許すため、年度未指定にも一意性を適用する。
        Index(
            "uq_course_offering",
            "course_id",
            "term_code",
            "semester_order",
            text("coalesce(academic_year, 0)"),
            unique=True,
        ),
        Index("ix_course_offering_term_course", "term_code", "course_id"),
        text_check("term_code"),
        integer_check("semester_order", 1),
        integer_check("academic_year", 1, True),
        text_check("source_note", True),
    )
    course_id: str = Field(foreign_key="courses.id", ondelete="RESTRICT")
    term_code: str
    # 年度未指定の繰り返し開講を保持するため、代理キーを使用する。
    id: str = Field(primary_key=True)
    semester_order: int
    academic_year: int | None = None
    source_note: str | None = None


class CurriculumSubject(SQLModel, table=True):
    __tablename__ = "curriculum_courses"
    __table_args__ = (
        ForeignKeyConstraint(
            ["curriculum_id", "classification_id"],
            ["classifications.curriculum_id", "classifications.id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("course_type IN ('required', 'selective', 'elective')"),
        integer_check("display_order"),
        Index(
            "ix_curriculum_course_classification",
            "curriculum_id",
            "classification_id",
            "display_order",
        ),
    )
    curriculum_id: str = Field(
        primary_key=True, foreign_key="curricula.id", ondelete="RESTRICT"
    )
    course_id: str = Field(
        primary_key=True, foreign_key="courses.id", ondelete="RESTRICT"
    )
    classification_id: str
    course_type: str
    display_order: int = 0


SUBJECT_TABLES = [
    SQLModel.metadata.tables[model.__tablename__]
    for model in (
        AcademicProgram,
        Curriculum,
        Classification,
        Subject,
        SubjectOffering,
        CurriculumSubject,
    )
]
