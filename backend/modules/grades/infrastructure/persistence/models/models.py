"""本人成績の履修回次テーブル。業務層の入出力契約とは分離する。"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlmodel import Field, SQLModel

from modules.subjects.infrastructure.persistence.models.subject_models import (
    integer_check,
)
from shared.infrastructure.persistence.types import UtcDateTime


class GradeAttemptRecord(SQLModel, table=True):
    __tablename__ = "grade_attempts"
    __table_args__ = (
        UniqueConstraint("student_id", "course_id", "attempt_no"),
        integer_check("attempt_no", 1),
        CheckConstraint("result_status IN ('finalized', 'pending')"),
        CheckConstraint(
            "grade_code IS NULL OR grade_code IN ('S', 'A', 'B', 'C', 'D', 'X')"
        ),
        CheckConstraint(
            "(result_status = 'finalized' AND grade_code IS NOT NULL) "
            "OR (result_status = 'pending' AND grade_code IS NULL)"
        ),
        integer_check("academic_year", 1, True),
        CheckConstraint("term_code IS NULL OR term_code IN ('first', 'second')"),
    )
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    student_id: str = Field(foreign_key="students.id")
    # 他学部の成績も保存するため、本人課程の課程別科目ではなく科目へ参照する。
    course_id: str = Field(foreign_key="courses.id", ondelete="RESTRICT")
    attempt_no: int
    result_status: str
    grade_code: str | None = None
    academic_year: int | None = None
    term_code: str | None = None
    updated_at: datetime = Field(sa_type=UtcDateTime)


GRADE_TABLES = [SQLModel.metadata.tables[GradeAttemptRecord.__tablename__]]
