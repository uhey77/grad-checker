"""本人成績の全集合を取得・置換する契約。"""

from collections import defaultdict
from typing import Literal, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from modules.grades.grad_checker_grades.application.errors.grades import GradeError
from modules.grades.grad_checker_grades.domain.grade import (
    GradeCode,
    ResultStatus,
    is_valid_attempt_sequence,
)

MAX_ATTEMPT_NO = 20
MAX_GRADES = 1000
MIN_ACADEMIC_YEAR = 1900
MAX_ACADEMIC_YEAR = 2100

type GradeCodeValue = Literal["S", "A", "B", "C", "D", "X"]
type ResultStatusValue = Literal["finalized", "pending"]
type TermCode = Literal["first", "second"]


class GradeAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    course_id: str = Field(min_length=36, max_length=36)
    attempt_no: int = Field(ge=1, le=MAX_ATTEMPT_NO)
    result_status: ResultStatusValue
    grade_code: GradeCodeValue | None
    academic_year: int | None = Field(ge=MIN_ACADEMIC_YEAR, le=MAX_ACADEMIC_YEAR)
    term_code: TermCode | None

    @model_validator(mode="after")
    def status_matches_grade(self) -> Self:
        if (self.result_status == "finalized") != (self.grade_code is not None):
            raise ValueError("finalized requires grade_code and pending forbids it")
        return self


class GradeSet(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    expected_revision: int = Field(ge=0, le=9007199254740990)
    grades: list[GradeAttempt] = Field(max_length=MAX_GRADES)


class StudentGrades(BaseModel):
    grades: list[GradeAttempt]
    data_revision: int


class GradeRepository(Protocol):
    def get_grades(self, student_id: str) -> StudentGrades: ...
    def replace_grades(self, student_id: str, grade_set: GradeSet) -> StudentGrades: ...


def check_attempts(grades: list[GradeAttempt]) -> None:
    by_course: defaultdict[str, list[GradeAttempt]] = defaultdict(list)
    for grade in grades:
        by_course[grade.course_id].append(grade)
    for attempts in by_course.values():
        if len({attempt.attempt_no for attempt in attempts}) != len(attempts):
            raise GradeError("duplicate_attempt")
        ordered = sorted(attempts, key=lambda attempt: attempt.attempt_no)
        sequence = [
            (
                attempt.attempt_no,
                ResultStatus(attempt.result_status),
                None if attempt.grade_code is None else GradeCode(attempt.grade_code),
            )
            for attempt in ordered
        ]
        if not is_valid_attempt_sequence(sequence):
            raise GradeError("invalid_attempt_sequence")


class GradeService:
    def __init__(self, repository: GradeRepository) -> None:
        self.repository = repository

    def get_grades(self, student_id: str) -> StudentGrades:
        return self.repository.get_grades(student_id)

    def save_grades(self, student_id: str, grade_set: GradeSet) -> StudentGrades:
        # 省略した回次は取消になるため、全集合を検証してから置換する。
        check_attempts(grade_set.grades)
        return self.repository.replace_grades(student_id, grade_set)
