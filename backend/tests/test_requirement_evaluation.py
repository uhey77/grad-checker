"""単位計算の境界、未確認規則、CS4課程のマスタ接続を検証する。"""

from pathlib import Path
from uuid import UUID

import pytest

from modules.grades.grad_checker_grades.application.dto.grades import GradeAttempt
from modules.requirements.grad_checker_requirements.application.dto import (
    evaluation as evaluation_models,
)
from modules.requirements.grad_checker_requirements.application.dto.seed import (
    RequirementSeed,
)
from modules.requirements.grad_checker_requirements.application.errors import (
    evaluation as evaluation_errors,
)
from modules.requirements.grad_checker_requirements.application.services import (
    evaluation as evaluation_services,
)
from modules.subjects.grad_checker_subjects.application.dto.subject_data import (
    SubjectDataSeed,
)
from modules.subjects.grad_checker_subjects.domain import curriculum_verification_status

VerificationStatus = curriculum_verification_status.VerificationStatus

BACKEND = Path(__file__).resolve().parents[1]


def uid(number):
    return UUID(int=number)


def grade(course_id, code="A", attempt=1, year=None, term=None):
    return GradeAttempt(
        course_id=str(course_id),
        attempt_no=attempt,
        result_status="pending" if code is None else "finalized",
        grade_code=code,
        academic_year=year,
        term_code=term,
    )


@pytest.fixture
def snapshot():
    # 実マスタを変更しない小さな架空課程。必要10単位、全科目14単位。
    source = {"source_document": "テスト専用", "source_pages": "1"}
    subjects = SubjectDataSeed.model_validate(
        {
            "academic_programs": [
                {"id": uid(1), "code": "test", "faculty_name": "試験"}
            ],
            "curricula": [
                {
                    **source,
                    "id": uid(2),
                    "program_id": uid(1),
                    "code": "test",
                    "name": "試験課程",
                    "revision": 3,
                    "admission_year_from": 2026,
                    "verification_status": "verified",
                }
            ],
            "classifications": [
                {
                    "id": uid(3),
                    "curriculum_id": uid(2),
                    "code": "root",
                    "name": "区分",
                    "level": 0,
                }
            ],
            "courses": [
                {
                    "id": uid(i),
                    "code": f"c{i}",
                    "name": f"科目{i}",
                    "credits": 4 if i == 15 else 2,
                    "offering_program_id": uid(1),
                    "teaching_type": "lecture",
                    "teaching_type_label": "講義",
                }
                for i in range(10, 16)
            ],
            "course_offerings": [],
            "curriculum_courses": [
                {
                    "curriculum_id": uid(2),
                    "course_id": uid(i),
                    "classification_id": uid(3),
                    "course_type": "required"
                    if i == 10
                    else "selective"
                    if i < 14
                    else "elective",
                }
                for i in range(10, 16)
            ],
        }
    )
    rows = [
        (20, "total", 10, None),
        (21, "classification_total", 10, 20),
        (22, "required_courses", 2, 21),
        (23, "selective_group", 2, 21),
        (24, "subminimum", 2, 23),
        (25, "selective_group", 2, 21),
        (26, "elective_total", 4, 21),
    ]
    scopes = {20: None, 21: None, 22: [10], 23: [11, 12], 24: [11], 25: [13], 26: None}
    requirements = RequirementSeed.model_validate(
        {
            "graduation_requirements": [
                {
                    **source,
                    "id": uid(i),
                    "curriculum_id": uid(2),
                    "code": f"r{i}",
                    "name": f"条件{i}",
                    "kind": kind,
                    "required_credits": required,
                    "parent_id": uid(parent) if parent else None,
                    "classification_id": uid(3) if parent else None,
                    "display_order": i,
                }
                for i, kind, required, parent in rows
            ],
            "requirement_scopes": [
                {
                    "id": uid(i * 100 + (course or 0)),
                    "curriculum_id": uid(2),
                    "requirement_id": uid(i),
                    "course_id": uid(course) if course else None,
                    "classification_id": None if course else uid(3),
                }
                for i, targets in scopes.items()
                for course in (targets or [None])
            ],
            "credit_rules": [
                {
                    **source,
                    "id": uid(30),
                    "curriculum_id": uid(2),
                    "code": "overflow",
                    "kind": "selective_overflow",
                    "verification_status": "verified",
                    "source_note": "同区分超過換算",
                    "revision": 2,
                }
            ],
            "credit_rule_courses": [
                {
                    "curriculum_id": uid(2),
                    "rule_id": uid(30),
                    "course_id": uid(i),
                    "target_classification_id": uid(3),
                }
                for i in (11, 12, 13)
            ],
            "credit_rule_limits": [],
        }
    )
    return evaluation_models.EvaluationSnapshot(
        program_id=uid(1),
        curriculum_id=uid(2),
        data_revision=7,
        subjects=subjects,
        requirements=requirements,
        grades=[],
    )


def conditions(result):
    return {row.code: row for row in result.requirements}


def assert_error(snapshot, code):
    with pytest.raises(evaluation_errors.EvaluationError) as caught:
        evaluation_services.evaluate_graduation(snapshot)
    assert caught.value.code == code
    assert caught.value.reason
    return caught.value


def test_empty_grades_are_normal_failure(snapshot):
    result = evaluation_services.evaluate_graduation(snapshot)
    assert result.result == "fail"
    assert result.total.model_dump() == {
        "required_credits": 10,
        "earned_credits": 0,
        "credited_credits": 0,
        "shortage": 10,
        "result": "fail",
    }
    assert [row.course_id for row in result.missing_required_courses] == [uid(10)]
    assert all(row.status == "not_taken" for row in result.courses)


@pytest.mark.parametrize("code", ["S", "A", "B", "C", "D", "X", None])
def test_grade_statuses(snapshot, code):
    snapshot.grades = [grade(uid(10), code)]
    result = evaluation_services.evaluate_graduation(snapshot)
    earned = code in {"S", "A", "B", "C"}
    assert result.total.earned_credits == (2 if earned else 0)
    assert result.courses[0].status == (
        "earned" if earned else "pending" if code is None else "not_earned"
    )


def test_retake_uses_latest_attempt_and_never_counts_twice(snapshot):
    snapshot.grades = [
        grade(uid(10), "B", 2, 2026, "second"),
        grade(uid(10), "D", 1, 2025, "first"),
    ]
    result = evaluation_services.evaluate_graduation(snapshot)
    assert result.total.earned_credits == 2
    assert result.courses[0].latest_attempt == snapshot.grades[0]


@pytest.mark.parametrize(
    "grades",
    [
        [("A", 1), ("B", 2)],
        [(None, 1), ("A", 2)],
        [("D", 1), ("A", 3)],
        [("A", 2)],
        [("D", 1), ("A", 1)],
    ],
)
def test_invalid_attempts_are_errors(snapshot, grades):
    snapshot.grades = [grade(uid(10), code, attempt) for code, attempt in grades]
    assert_error(
        snapshot,
        "duplicate_attempt" if grades[-1][1] == 1 else "invalid_attempt_sequence",
    )


def test_all_conditions_pass_and_overflow_does_not_create_credits(snapshot):
    snapshot.grades = [grade(uid(i)) for i in range(10, 16)]
    before = snapshot.model_dump_json()
    result = evaluation_services.evaluate_graduation(snapshot)
    rows = conditions(result)
    assert result.result == "pass"
    assert result.total.earned_credits == result.total.credited_credits == 14
    assert rows["r23"].earned_credits == 4
    assert rows["r23"].credited_credits == 2
    assert rows["r26"].earned_credits == 6
    assert rows["r26"].credited_credits == 8
    assert len(result.allocations) == 1
    assert result.allocations[0].transferred_credits == 2
    assert result.missing_required_courses == []
    assert result.data_revision == 7 and result.curriculum.revision == 3
    assert result.rule_revisions == {uid(30): 2}
    assert snapshot.model_dump_json() == before
    snapshot.grades.reverse()
    snapshot.requirements.graduation_requirements.reverse()
    assert evaluation_services.evaluate_graduation(snapshot) == result


def test_exact_threshold_and_overflow_boundary(snapshot):
    snapshot.grades = [grade(uid(i)) for i in (10, 11, 13, 15)]
    result = evaluation_services.evaluate_graduation(snapshot)
    assert result.result == "pass"
    assert result.total.earned_credits == 10
    assert result.allocations == []
    snapshot.grades = [grade(uid(i)) for i in (10, 11, 13, 14)]
    result = evaluation_services.evaluate_graduation(snapshot)
    assert result.total.shortage == 2
    assert conditions(result)["r26"].shortage == 2


@pytest.mark.parametrize("missing", [10, 13])
def test_total_surplus_does_not_cover_required_or_other_group(snapshot, missing):
    snapshot.grades = [grade(uid(i)) for i in range(10, 16) if i != missing]
    result = evaluation_services.evaluate_graduation(snapshot)
    assert result.total.shortage == 0
    assert result.total.result == "pass"
    assert result.result == "fail"
    assert conditions(result)["r22" if missing == 10 else "r25"].shortage == 2


def test_subminimum_is_independent_even_when_group_and_total_pass(snapshot):
    snapshot.grades = [grade(uid(i)) for i in (10, 12, 13, 14, 15)]
    result = evaluation_services.evaluate_graduation(snapshot)
    assert result.total.shortage == 0
    assert conditions(result)["r23"].result == "pass"
    assert conditions(result)["r24"].shortage == 2
    assert result.result == "fail"


def test_unverified_overflow_only_blocks_dependent_cases(snapshot):
    rule = snapshot.requirements.credit_rules[0]
    rule.verification_status = VerificationStatus.UNVERIFIED
    rule.unresolved_reason = "Q02の内訳配分を確認中"
    snapshot.grades = [grade(uid(11))]
    assert evaluation_services.evaluate_graduation(snapshot).result == "fail"
    snapshot.grades.append(grade(uid(12)))
    error = assert_error(snapshot, "unverified_credit_rule")
    assert error.rule_id == rule.id and error.reason == rule.unresolved_reason


def test_missing_overflow_mapping_is_not_silently_discarded(snapshot):
    snapshot.grades = [grade(uid(11)), grade(uid(12))]
    snapshot.requirements.credit_rule_courses.pop(0)
    assert_error(snapshot, "invalid_evaluation_master")


def test_overflow_with_missing_subminimum_is_normal_failure(snapshot):
    snapshot.subjects.courses[2].credits = 4
    snapshot.grades = [grade(uid(12))]
    result = evaluation_services.evaluate_graduation(snapshot)
    assert result.result == "fail"
    assert result.allocations[0].transferred_credits == 2
    assert conditions(result)["r24"].shortage == 2
    assert result.total.credited_credits == 4


def test_external_rule_does_not_guess_unmapped_course(snapshot):
    external = snapshot.subjects.courses[0].model_copy(
        update={"id": uid(99), "code": "external"}
    )
    snapshot.subjects.courses.append(external)
    data = snapshot.requirements.model_dump()
    data["credit_rules"].append(
        {
            "id": uid(31),
            "curriculum_id": uid(2),
            "code": "external",
            "kind": "other_faculty",
            "verification_status": "unverified",
            "source_document": "テスト専用",
            "source_pages": "1",
            "source_note": "共通上限",
            "revision": 1,
            "unresolved_reason": "Q09確認中",
        }
    )
    data["credit_rule_limits"].append(
        {
            "id": uid(32),
            "rule_id": uid(31),
            "limit_group_code": "all",
            "max_credits": 6,
        }
    )
    snapshot.requirements = RequirementSeed.model_validate(data)
    snapshot.grades = [grade(uid(99))]
    assert_error(snapshot, "unsupported_external_credits")


def test_missing_selective_group_and_overlapping_groups_are_errors(snapshot):
    group = next(
        r for r in snapshot.requirements.graduation_requirements if r.id == uid(25)
    )
    scope = next(
        r
        for r in snapshot.requirements.requirement_scopes
        if r.requirement_id == uid(25)
    )
    scope.course_id = uid(11)
    assert_error(snapshot, "invalid_evaluation_master")
    snapshot.requirements.graduation_requirements.remove(group)
    snapshot.requirements.requirement_scopes.remove(scope)
    assert_error(snapshot, "invalid_evaluation_master")


def test_external_earned_courses_are_not_ignored(snapshot):
    external = snapshot.subjects.courses[0].model_copy(
        update={"id": uid(99), "code": "external"}
    )
    snapshot.subjects.courses.append(external)
    snapshot.grades = [grade(uid(99), "D")]
    assert evaluation_services.evaluate_graduation(snapshot).total.earned_credits == 0
    snapshot.grades = [grade(uid(99))]
    assert_error(snapshot, "unsupported_external_credits")


def test_unknown_course_and_invalid_uuid_are_errors(snapshot):
    snapshot.grades = [grade(uid(99))]
    assert_error(snapshot, "unknown_course")
    snapshot.grades[0] = snapshot.grades[0].model_copy(update={"course_id": "x" * 36})
    assert_error(snapshot, "invalid_grades")


@pytest.mark.parametrize(
    "field,value",
    [
        ("grade_code", "R"),
        ("grade_code", None),
        ("result_status", "pending"),
    ],
)
def test_revalidate_mutated_grade_models(snapshot, field, value):
    snapshot.grades = [grade(uid(10))]
    snapshot.grades[0] = snapshot.grades[0].model_copy(update={field: value})
    assert_error(snapshot, "invalid_evaluation_input")


@pytest.mark.parametrize("credit_value", [0, -1, 1.5, True])
def test_invalid_credit_values_are_errors(snapshot, credit_value):
    snapshot.subjects.courses[0].credits = credit_value
    assert_error(snapshot, "invalid_evaluation_input")


def test_missing_total_or_required_conditions_are_errors(snapshot):
    snapshot.requirements.graduation_requirements = []
    snapshot.requirements.requirement_scopes = []
    assert_error(snapshot, "invalid_evaluation_master")


def test_missing_required_condition_does_not_produce_pass(snapshot):
    snapshot.requirements.graduation_requirements = [
        r for r in snapshot.requirements.graduation_requirements if r.id != uid(22)
    ]
    snapshot.requirements.requirement_scopes = [
        r
        for r in snapshot.requirements.requirement_scopes
        if r.requirement_id != uid(22)
    ]
    assert_error(snapshot, "invalid_evaluation_master")


def test_classification_cycle_and_profile_mismatch_are_errors(snapshot):
    snapshot.program_id = uid(99)
    assert_error(snapshot, "invalid_evaluation_master")
    snapshot.program_id = uid(1)
    snapshot.subjects.classifications[0].parent_id = uid(3)
    assert_error(snapshot, "invalid_evaluation_master")


@pytest.mark.parametrize("index", range(4))
def test_cs_seed_calculates_without_changing_admission_year_confirmation(index):
    subjects = SubjectDataSeed.model_validate_json(
        (BACKEND / "seeds/cs_2026.json").read_text()
    )
    requirements = RequirementSeed.model_validate_json(
        (BACKEND / "seeds/cs_requirements_2026.json").read_text()
    )
    curriculum = subjects.curricula[index]
    snapshot = evaluation_models.EvaluationSnapshot(
        program_id=curriculum.program_id,
        curriculum_id=curriculum.id,
        data_revision=0,
        subjects=subjects,
        requirements=requirements,
        grades=[],
    )
    result = evaluation_services.evaluate_graduation(snapshot)
    assert result.result == "fail"
    assert result.curriculum.verification_status == VerificationStatus.UNVERIFIED
    assert result.curriculum.admission_year_from is None
    assert result.curriculum.admission_year_to is None
    assert len(result.requirements) == 20
    assert result.total.shortage == 124
    assert sorted(row.required_credits for row in result.categories) == [38, 42, 44]
    # 実シードのままで必修1科目の修得・算入・不足が反映される。
    required = next(
        row
        for row in subjects.curriculum_courses
        if row.curriculum_id == curriculum.id and row.course_type == "required"
    )
    course_credits = next(
        c.credits for c in subjects.courses if c.id == required.course_id
    )
    snapshot.grades = [grade(required.course_id)]
    result = evaluation_services.evaluate_graduation(snapshot)
    assert (
        result.total.earned_credits == result.total.credited_credits == course_credits
    )
    assert result.total.shortage == 124 - course_credits
    assert all(
        c.course_id != required.course_id for c in result.missing_required_courses
    )
    # 原本を再確認した実シードのまま、全科目修得と超過換算を検証する。
    snapshot.grades = [
        grade(row.course_id)
        for row in subjects.curriculum_courses
        if row.curriculum_id == curriculum.id
    ]
    result = evaluation_services.evaluate_graduation(snapshot)
    assert result.result == "pass"
    assert result.total.earned_credits == result.total.credited_credits
    assert result.total.shortage == 0
