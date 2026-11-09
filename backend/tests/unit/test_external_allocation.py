"""架空の照合済み科目で取得順・同時期の配分と不足時期の入力要求を検証する。"""

import pytest

from modules.requirements.application.services import evaluation as evaluation_services
from tests.support.graduation import add_external, assert_error, uid


def allocations(result):
    return {
        row.target_classification_id: row.credited_credits
        for row in result.external_allocations
    }


def test_same_period_can_meet_all_conditions_without_double_counting(external_snapshot):
    sample = external_snapshot
    add_external(sample)
    before = sample.model_dump_json()
    result = evaluation_services.evaluate_graduation(sample)
    assert result.result == "pass"
    assert allocations(result) == {uid(3): 2, uid(4): 4}
    assert result.total.earned_credits == 16
    assert result.total.credited_credits == 14
    assert sum(row.free_credits for row in result.external_allocations) == 2
    assert result.warnings == ["provisional_external_allocation"]
    assert sample.model_dump_json() == before
    sample.grades.reverse()
    sample.requirements.credit_rule_courses.reverse()
    assert evaluation_services.evaluate_graduation(sample) == result


def test_chronology_precedes_optimization(external_snapshot):
    add_external(external_snapshot, (100, 101), 2025, "second")
    add_external(external_snapshot, (102, 103), 2026, "first")
    result = evaluation_services.evaluate_graduation(external_snapshot)
    assert allocations(result) == {uid(3): 4, uid(4): 2}
    assert result.result == "fail"
    assert result.total.shortage == 0  # 総単位が足りても区分不足を隠さない。


@pytest.mark.parametrize("year,term", [(None, None), (2026, None), (None, "first")])
def test_missing_period_is_required_only_when_allocation_can_change(
    external_snapshot, year, term
):
    add_external(external_snapshot, year=year, term=term)
    assert_error(external_snapshot, "external_acquisition_period_required")


def test_within_cap_requires_no_period_and_has_no_warning(external_snapshot):
    add_external(external_snapshot, (100, 102, 103), None, None)
    result = evaluation_services.evaluate_graduation(external_snapshot)
    assert result.result == "pass"
    assert result.warnings == []
    assert sum(row.free_credits for row in result.external_allocations) == 0


def test_one_destination_needs_no_period_even_over_cap(external_snapshot):
    for row in external_snapshot.requirements.credit_rule_courses:
        if row.rule_id == uid(31):
            row.target_classification_id = uid(3)
    add_external(external_snapshot, year=None, term=None)
    result = evaluation_services.evaluate_graduation(external_snapshot)
    assert allocations(result) == {uid(3): 6}
    assert result.warnings == []


def test_missing_term_after_cap_cannot_change_result(external_snapshot):
    add_external(external_snapshot, (100, 102, 103), 2025, "second")
    add_external(external_snapshot, (101,), 2026, None)
    result = evaluation_services.evaluate_graduation(external_snapshot)
    assert result.result == "pass"
    assert allocations(result) == {uid(3): 2, uid(4): 4}


def test_missing_term_before_cap_cannot_change_result(external_snapshot):
    add_external(external_snapshot, (100,), 2025, None)
    add_external(external_snapshot, (101, 102, 103), 2026, "first")
    assert evaluation_services.evaluate_graduation(external_snapshot).result == "pass"


def test_unmapped_courses_and_unadopted_policy_are_not_guessed(external_snapshot):
    add_external(external_snapshot)
    rule = next(
        row for row in external_snapshot.requirements.credit_rules if row.id == uid(31)
    )
    rule.allocation_policy = None
    assert_error(external_snapshot, "unverified_credit_rule")
    external_snapshot.requirements.credit_rule_courses = [
        row
        for row in external_snapshot.requirements.credit_rule_courses
        if row.course_id != uid(100)
    ]
    assert_error(external_snapshot, "unsupported_external_credits")
