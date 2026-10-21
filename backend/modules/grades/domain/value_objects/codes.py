"""成績記号・確定状態と合格の区分。"""

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
