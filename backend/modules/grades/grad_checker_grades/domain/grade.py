"""成績記号・確定状態と、同じ科目の履修回次の並び。"""

from collections.abc import Sequence
from enum import StrEnum


class ResultStatus(StrEnum):
    FINALIZED = "finalized"
    PENDING = "pending"


class GradeCode(StrEnum):
    S = "S"
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    X = "X"


PASSING_GRADE_CODES = frozenset({GradeCode.S, GradeCode.A, GradeCode.B, GradeCode.C})


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
