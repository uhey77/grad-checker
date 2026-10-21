"""成績の回次と保存済み成績セットの入出力。"""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
