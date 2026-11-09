"""卒業判定テストで共有する架空の課程と成績。"""

from pathlib import Path
from uuid import UUID

import pytest

from modules.grades.application.dto.grades import GradeAttempt
from modules.requirements.application.dto import evaluation as evaluation_models
from modules.requirements.application.dto.seed import RequirementSeed
from modules.requirements.application.errors import evaluation as evaluation_errors
from modules.requirements.application.services import evaluation as evaluation_services
from modules.subjects.application.dto.subject_data import SubjectDataSeed

BACKEND = Path(__file__).resolve().parents[2]


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


def assert_error(snapshot, code):
    with pytest.raises(evaluation_errors.EvaluationError) as caught:
        evaluation_services.evaluate_graduation(snapshot)
    assert caught.value.code == code
    assert caught.value.reason
    return caught.value


@pytest.fixture
def external_snapshot(snapshot):
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
