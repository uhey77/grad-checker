from collections.abc import Sequence

from modules.grades.domain.value_objects.codes import (
    PASSING_GRADE_CODES,
    GradeCode,
    ResultStatus,
)


def allows_retake(status: ResultStatus, grade_code: GradeCode | None) -> bool:
    # 再履修できるのは確定した不合格（D・未受験X）の後だけ。合格・未確定の後は不可。
    return (
        status == ResultStatus.FINALIZED
        and grade_code is not None
        and grade_code not in PASSING_GRADE_CODES
    )


def is_valid_attempt_sequence(
    attempts: Sequence[tuple[int, ResultStatus, GradeCode | None]],
) -> bool:
    """1科目の回次を昇順で受け取り、1からの連番と再履修の条件を確認する。"""
    numbers = [number for number, _, _ in attempts]
    if numbers != list(range(1, len(attempts) + 1)):
        return False
    return all(allows_retake(status, code) for _, status, code in attempts[:-1])
