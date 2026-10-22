"""成績記号・確定状態と、同じ科目の履修回次の並び。"""

from pydantic import BaseModel, ConfigDict, field_validator

from modules.grades.domain.errors.grade import InvalidCourseAttemptsError
from modules.grades.domain.services.retakes import is_valid_attempt_sequence
from modules.grades.domain.value_objects.codes import GradeCode, ResultStatus


class CourseAttempts(BaseModel):
    """一科目の履修回次。並び順を正規化し、重複・欠番・再履修条件を守る。"""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    attempts: tuple[tuple[int, ResultStatus, GradeCode | None], ...]

    @field_validator("attempts")
    @classmethod
    def valid_history(
        cls, attempts: tuple[tuple[int, ResultStatus, GradeCode | None], ...]
    ) -> tuple[tuple[int, ResultStatus, GradeCode | None], ...]:
        ordered = tuple(sorted(attempts, key=lambda attempt: attempt[0]))
        numbers = [number for number, _, _ in ordered]
        if len(set(numbers)) != len(numbers):
            raise InvalidCourseAttemptsError("duplicate_attempt")
        if not is_valid_attempt_sequence(ordered):
            raise InvalidCourseAttemptsError("invalid_attempt_sequence")
        if any(
            (status == ResultStatus.FINALIZED) != (code is not None)
            for _, status, code in ordered
        ):
            raise InvalidCourseAttemptsError("invalid_attempt_sequence")
        return ordered
