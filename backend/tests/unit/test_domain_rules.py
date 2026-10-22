"""DB・HTTPなしで業務上の不変条件と配分を検証する。"""

from uuid import UUID

import pytest
from pydantic import ValidationError

from modules.grades.domain.errors.grade import InvalidCourseAttemptsError
from modules.grades.domain.value_objects.codes import GradeCode, ResultStatus
from modules.grades.domain.value_objects.grade import CourseAttempts
from modules.requirements.domain.services.allocation import allocate_best_fit
from modules.requirements.domain.value_objects.credits import (
    AllocationTarget,
    CreditRequirement,
)


def test_course_attempts_normalize_without_mutating_and_remain_immutable():
    attempts = (
        (2, ResultStatus.PENDING, None),
        (1, ResultStatus.FINALIZED, GradeCode.D),
    )
    history = CourseAttempts(attempts=attempts)
    assert [a[0] for a in history.attempts] == [1, 2]
    assert attempts[0][0] == 2
    with pytest.raises(ValidationError, match="frozen_instance"):
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
            attempts=tuple(
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
    condition = CreditRequirement(required=required, credited=credited)
    assert (condition.shortage, condition.result) == (shortage, result)


def test_allocation_prefers_fulfilled_conditions_then_shortage_then_code():
    first, second = UUID(int=1), UUID(int=2)
    targets = [
        AllocationTarget(
            id=first,
            code="A",
            available_credits=4,
            conditions=(CreditRequirement(required=4, credited=0),),
        ),
        AllocationTarget(
            id=second,
            code="B",
            available_credits=4,
            conditions=(CreditRequirement(required=2, credited=0),),
        ),
    ]
    # Bの条件を達成し、残りをAへ振る。入力の順番で結果を変えない。
    assert allocate_best_fit(targets, 3) == {first: 1, second: 2}
    assert allocate_best_fit(list(reversed(targets)), 3) == {first: 1, second: 2}
    tied = [
        AllocationTarget(id=t.id, code=t.code, available_credits=4, conditions=())
        for t in targets
    ]
    assert allocate_best_fit(list(reversed(tied)), 3) == {first: 3, second: 0}
    assert allocate_best_fit(targets, 0) == {first: 0, second: 0}


@pytest.mark.parametrize("value", ["2", True, 2.0, -1])
def test_credit_values_reject_implicit_conversion_and_negative_credits(value):
    with pytest.raises(ValidationError):
        CreditRequirement(required=value, credited=0)
    with pytest.raises(ValidationError):
        CreditRequirement(required=2, credited=value)
    with pytest.raises(ValidationError):
        AllocationTarget(
            id=UUID(int=1), code="A", available_credits=value, conditions=()
        )


def test_value_objects_are_equal_hashable_and_reject_mutation():
    first = CreditRequirement(required=2, credited=1)
    assert first == CreditRequirement(required=2, credited=1)
    assert len({first, CreditRequirement(required=2, credited=1)}) == 1
    with pytest.raises(ValidationError, match="frozen_instance"):
        first.credited = 2  # ty: ignore[invalid-assignment]
    with pytest.raises(ValidationError):
        CreditRequirement.model_validate({"required": 2, "credited": 1, "shortage": 0})


@pytest.mark.parametrize(
    ("status", "grade"),
    [(ResultStatus.FINALIZED, None), (ResultStatus.PENDING, GradeCode.A)],
)
def test_domain_checks_status_and_grade_without_relying_on_api_dtos(status, grade):
    with pytest.raises(InvalidCourseAttemptsError, match="invalid_attempt_sequence"):
        CourseAttempts(attempts=((1, status, grade),))
