"""DB・HTTP・Pydanticなしで業務上の不変条件と配分を検証する。"""

from dataclasses import FrozenInstanceError
from uuid import UUID

import pytest

from modules.grades.grad_checker_grades.domain.grade import (
    CourseAttempts,
    GradeCode,
    InvalidCourseAttemptsError,
    ResultStatus,
)
from modules.requirements.grad_checker_requirements.domain.credits import (
    AllocationTarget,
    CreditRequirement,
    allocate_best_fit,
)


def test_course_attempts_normalize_without_mutating_and_remain_immutable():
    attempts = (
        (2, ResultStatus.PENDING, None),
        (1, ResultStatus.FINALIZED, GradeCode.D),
    )
    history = CourseAttempts(attempts)
    assert [a[0] for a in history.attempts] == [1, 2]
    assert attempts[0][0] == 2
    with pytest.raises(FrozenInstanceError):
        history.attempts = ()  # ty: ignore[invalid-assignment]


@pytest.mark.parametrize(
    ("attempts", "code"),
    [
        ([(1, "D"), (1, "A")], "duplicate_attempt"),
        ([(2, "A")], "invalid_attempt_sequence"),
        ([(1, "D"), (3, "A")], "invalid_attempt_sequence"),
        ([(1, "A"), (2, "D")], "invalid_attempt_sequence"),
        ([(1, None), (2, "A")], "invalid_attempt_sequence"),
    ],
)
def test_course_attempts_reject_invalid_history(attempts, code):
    with pytest.raises(InvalidCourseAttemptsError, match=code):
        CourseAttempts(
            tuple(
                (
                    number,
                    ResultStatus.PENDING if grade is None else ResultStatus.FINALIZED,
                    GradeCode(grade) if grade is not None else None,
                )
                for number, grade in attempts
            )
        )


@pytest.mark.parametrize(
    ("required", "credited", "shortage", "result"),
    [(10, 6, 4, "fail"), (10, 10, 0, "pass"), (10, 12, 0, "pass")],
)
def test_credit_requirement_counts_shortage_without_negative_values(
    required, credited, shortage, result
):
    condition = CreditRequirement(required, credited)
    assert (condition.shortage, condition.result) == (shortage, result)


def test_allocation_prefers_fulfilled_conditions_then_shortage_then_code():
    first, second = UUID(int=1), UUID(int=2)
    targets = [
        AllocationTarget(first, "A", 4, (CreditRequirement(4, 0),)),
        AllocationTarget(second, "B", 4, (CreditRequirement(2, 0),)),
    ]
    # Bの条件を達成し、残りをAへ振る。入力の順番で結果を変えない。
    assert allocate_best_fit(targets, 3) == {first: 1, second: 2}
    assert allocate_best_fit(list(reversed(targets)), 3) == {first: 1, second: 2}
    tied = [AllocationTarget(t.id, t.code, 4, ()) for t in targets]
    assert allocate_best_fit(list(reversed(tied)), 3) == {first: 3, second: 0}
    assert allocate_best_fit(targets, 0) == {first: 0, second: 0}
