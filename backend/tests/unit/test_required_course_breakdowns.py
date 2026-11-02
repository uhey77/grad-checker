"""必修内訳の必要・算入単位を実シードで検証し、判定値への影響を防ぐ。"""

from datetime import UTC, datetime

import pytest

from modules.requirements.application.dto.evaluation import EvaluationSnapshot
from modules.requirements.application.dto.seed import RequirementSeed
from modules.requirements.application.services.evaluation import evaluate_graduation
from modules.requirements.application.services.student_evaluation import (
    evaluate_student,
)
from modules.subjects.application.dto.subject_data import SubjectDataSeed
from tests.unit.test_requirement_evaluation import BACKEND, grade


def cs_snapshot(index):
    subjects = SubjectDataSeed.model_validate_json(
        (BACKEND / "seeds/cs_2026.json").read_text()
    )
    requirements = RequirementSeed.model_validate_json(
        (BACKEND / "seeds/cs_requirements_2026.json").read_text()
    )
    curriculum = subjects.curricula[index]
    return EvaluationSnapshot(
        program_id=curriculum.program_id,
        curriculum_id=curriculum.id,
        data_revision=0,
        subjects=subjects,
        requirements=requirements,
        grades=[],
    )


@pytest.mark.parametrize("index", range(4))
def test_required_breakdowns_match_verified_source_without_changing_judgment(index):
    snapshot = cs_snapshot(index)
    baseline = evaluate_graduation(snapshot)
    result = evaluate_student(snapshot, datetime(2026, 10, 26, tzinfo=UTC))
    by_code = {row.code: row for row in result.required_course_breakdowns}
    social = snapshot.subjects.curricula[index].code.startswith("CS-SOCIAL")
    expected = {
        "general.language.required_breakdown": 4,
        "general.information-math.required_breakdown": 6,
        "general.career.required_breakdown": 6,
        "foundation.math.required_breakdown": 4,
        "foundation.computer-business.required_breakdown": 14 if social else 17,
        "specialized.experiment.required_breakdown": 21,
    }
    assert {code: row.required_credits for code, row in by_code.items()} == expected
    assert all(row.credited_credits == 0 for row in by_code.values())
    assert (
        result.model_dump(exclude={"evaluated_at", "required_course_breakdowns"})
        == baseline.model_dump()
    )
    assert len(result.requirements) == 20
    assert result.total.required_credits == 124
    parents = {row.id: row for row in result.requirements}
    for row in by_code.values():
        assert row.parent_id is not None
        assert parents[row.parent_id].kind == "classification_total"
        assert row.classification_id is not None
    assert sum(row.required_credits for row in by_code.values()) == (
        55 if social else 58
    )


@pytest.mark.parametrize("grade_code", ["A", "D", None])
def test_experiment_required_credits_use_saved_grades_and_exclude_selective_courses(
    grade_code,
):
    snapshot = cs_snapshot(0)
    experiment = next(
        c
        for c in snapshot.subjects.classifications
        if c.curriculum_id == snapshot.curriculum_id
        and c.code == "specialized.experiment"
    )
    associations = [
        row
        for row in snapshot.subjects.curriculum_courses
        if row.curriculum_id == snapshot.curriculum_id
        and row.classification_id == experiment.id
    ]
    required = next(row for row in associations if row.course_type == "required")
    selective = next(row for row in associations if row.course_type == "selective")
    snapshot.grades = [
        grade(required.course_id, grade_code),
        grade(selective.course_id),
    ]
    before = snapshot.model_dump_json()
    result = evaluate_student(snapshot, datetime(2026, 10, 26, tzinfo=UTC))
    row = next(
        row
        for row in result.required_course_breakdowns
        if row.classification_id == experiment.id
    )
    credit = next(
        course.credits
        for course in snapshot.subjects.courses
        if course.id == required.course_id
    )
    assert row.required_credits == 21
    assert row.credited_credits == (credit if grade_code == "A" else 0)
    assert row.earned_credits == row.credited_credits
    assert row.shortage == 21 - row.credited_credits
    assert snapshot.model_dump_json() == before
