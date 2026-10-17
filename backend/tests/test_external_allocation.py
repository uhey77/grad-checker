"""架空の照合済み科目で取得順・同時期の配分と不足時期の入力要求を検証する。"""

import pytest
from test_requirement_evaluation import assert_error, grade, snapshot, uid  # noqa: F401

from modules.requirements.grad_checker_requirements.application import evaluation_models
from modules.requirements.grad_checker_requirements.application.evaluation import (
    evaluate_graduation,
)


@pytest.fixture
def external_snapshot(snapshot):  # noqa: F811
    data = snapshot.model_dump(mode="json")
    subjects = data["subjects"]
    subjects["academic_programs"].append(
        {"id": str(uid(90)), "code": "external", "faculty_name": "別学部"}
    )
    subjects["classifications"].append(
        {
            **subjects["classifications"][0],
            "id": str(uid(4)),
            "code": "second",
            "name": "第二区分",
        }
    )
    subjects["courses"].append(
        {**subjects["courses"][0], "id": str(uid(16)), "code": "c16", "credits": 4}
    )
    subjects["curriculum_courses"].append(
        {
            **subjects["curriculum_courses"][-1],
            "course_id": str(uid(16)),
            "classification_id": str(uid(4)),
            "course_type": "elective",
        }
    )
    requirements = data["requirements"]
    requirements["graduation_requirements"][0]["required_credits"] = 14
    for number, kind, parent in [
        (40, "classification_total", 20),
        (41, "elective_total", 40),
    ]:
        requirements["graduation_requirements"].append(
            {
                **requirements["graduation_requirements"][1],
                "id": str(uid(number)),
                "code": f"r{number}",
                "kind": kind,
                "required_credits": 4,
                "classification_id": str(uid(4)),
                "parent_id": str(uid(parent)),
            }
        )
    for number in (20, 40, 41):
        requirements["requirement_scopes"].append(
            {
                "id": str(uid(4000 + number)),
                "curriculum_id": str(uid(2)),
                "requirement_id": str(uid(number)),
                "classification_id": str(uid(4)),
            }
        )
    requirements["credit_rules"].append(
        {
            **requirements["credit_rules"][0],
            "id": str(uid(31)),
            "code": "external",
            "kind": "other_faculty",
            "verification_status": "unverified",
            "unresolved_reason": "大学の配分順序は未確認。アプリの仮定で計算。",
            "allocation_policy": "chronological_best_fit_v1",
        }
    )
    requirements["credit_rule_limits"].append(
        {
            "id": str(uid(32)),
            "rule_id": str(uid(31)),
            "limit_group_code": "shared",
            "max_credits": 6,
        }
    )
    for number, root in [(100, 3), (101, 3), (102, 4), (103, 4)]:
        subjects["courses"].append(
            {
                **subjects["courses"][0],
                "id": str(uid(number)),
                "code": f"external{number}",
                "name": f"他学部科目{number}",
                "offering_program_id": str(uid(90)),
            }
        )
        requirements["credit_rule_courses"].append(
            {
                "curriculum_id": str(uid(2)),
                "rule_id": str(uid(31)),
                "course_id": str(uid(number)),
                "target_classification_id": str(uid(root)),
            }
        )
    data["grades"] = [grade(uid(i)).model_dump() for i in (10, 11, 13, 14)]
    return evaluation_models.EvaluationSnapshot.model_validate(data)


def add_external(sample, numbers=(100, 101, 102, 103), year=2026, term="first"):
    sample.grades.extend(grade(uid(i), year=year, term=term) for i in numbers)


def allocations(result):
    return {
        row.target_classification_id: row.credited_credits
        for row in result.external_allocations
    }


def test_same_period_can_meet_all_conditions_without_double_counting(external_snapshot):
    sample = external_snapshot
    add_external(sample)
    before = sample.model_dump_json()
    result = evaluate_graduation(sample)
    assert result.result == "pass"
    assert allocations(result) == {uid(3): 2, uid(4): 4}
    assert result.total.earned_credits == 16
    assert result.total.credited_credits == 14
    assert sum(row.free_credits for row in result.external_allocations) == 2
    assert result.warnings == ["provisional_external_allocation"]
    assert sample.model_dump_json() == before
    sample.grades.reverse()
    sample.requirements.credit_rule_courses.reverse()
    assert evaluate_graduation(sample) == result


def test_chronology_precedes_optimization(external_snapshot):
    add_external(external_snapshot, (100, 101), 2025, "second")
    add_external(external_snapshot, (102, 103), 2026, "first")
    result = evaluate_graduation(external_snapshot)
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
    result = evaluate_graduation(external_snapshot)
    assert result.result == "pass"
    assert result.warnings == []
    assert sum(row.free_credits for row in result.external_allocations) == 0


def test_one_destination_needs_no_period_even_over_cap(external_snapshot):
    for row in external_snapshot.requirements.credit_rule_courses:
        if row.rule_id == uid(31):
            row.target_classification_id = uid(3)
    add_external(external_snapshot, year=None, term=None)
    result = evaluate_graduation(external_snapshot)
    assert allocations(result) == {uid(3): 6}
    assert result.warnings == []


def test_missing_term_after_cap_cannot_change_result(external_snapshot):
    add_external(external_snapshot, (100, 102, 103), 2025, "second")
    add_external(external_snapshot, (101,), 2026, None)
    result = evaluate_graduation(external_snapshot)
    assert result.result == "pass"
    assert allocations(result) == {uid(3): 2, uid(4): 4}


def test_missing_term_before_cap_cannot_change_result(external_snapshot):
    add_external(external_snapshot, (100,), 2025, None)
    add_external(external_snapshot, (101, 102, 103), 2026, "first")
    assert evaluate_graduation(external_snapshot).result == "pass"


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
