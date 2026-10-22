"""成績入力をDomainの回次・再履修ルールで検証する。"""

from collections import defaultdict

from modules.grades.application.dto.grades import GradeAttempt
from modules.grades.application.errors.grades import GradeError
from modules.grades.domain.errors.grade import InvalidCourseAttemptsError
from modules.grades.domain.value_objects.codes import GradeCode, ResultStatus
from modules.grades.domain.value_objects.grade import CourseAttempts


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
