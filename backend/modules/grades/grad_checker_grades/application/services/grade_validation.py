"""成績入力をDomainの回次・再履修ルールで検証する。"""

from collections import defaultdict

from ...domain.grade import (
    CourseAttempts,
    GradeCode,
    InvalidCourseAttemptsError,
    ResultStatus,
)
from ..dto.grades import GradeAttempt
from ..errors.grades import GradeError


def check_attempts(grades: list[GradeAttempt]) -> None:
    by_course: defaultdict[str, list[GradeAttempt]] = defaultdict(list)
    for grade in grades:
        by_course[grade.course_id].append(grade)
    for attempts in by_course.values():
        try:
            CourseAttempts(
                attempts=tuple(
                    (
                        attempt.attempt_no,
                        ResultStatus(attempt.result_status),
                        None
                        if attempt.grade_code is None
                        else GradeCode(attempt.grade_code),
                    )
                    for attempt in attempts
                )
            )
        except InvalidCourseAttemptsError as error:
            raise GradeError(error.code) from error
