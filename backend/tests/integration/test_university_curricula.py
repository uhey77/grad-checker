"""全学部・大学院の出典集合と、学部から独立した修了判定を検証する。"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from modules.grades.application.dto.grades import GradeAttempt
from modules.requirements.application.dto import check_results as check_results_dto
from modules.requirements.application.dto import completion_policy
from modules.requirements.application.dto import evaluation as evaluation_models
from modules.requirements.application.dto.seed import RequirementSeed
from modules.requirements.application.errors import evaluation
from modules.requirements.application.services import evaluation as evaluation_services
from modules.requirements.application.services import validation as validation_services
from modules.subjects.application.dto.subject_data import SubjectDataSeed

SEEDS = Path(__file__).resolve().parents[2] / "seeds"


@pytest.fixture(scope="module")
def masters():
    subjects = SubjectDataSeed.model_validate_json(
        (SEEDS / "university_2026.json").read_text()
    )
    requirements = RequirementSeed.model_validate_json(
        (SEEDS / "university_requirements_2026.json").read_text()
    )
    cs_subjects = SubjectDataSeed.model_validate_json(
        (SEEDS / "cs_2026.json").read_text()
    )
    cs_requirements = RequirementSeed.model_validate_json(
        (SEEDS / "cs_requirements_2026.json").read_text()
    )
    subjects = SubjectDataSeed(
        **{
            k: getattr(cs_subjects, k) + getattr(subjects, k)
            for k in SubjectDataSeed.model_fields
        }
    )
    requirements = RequirementSeed(
        **{
            k: getattr(cs_requirements, k) + getattr(requirements, k)
            for k in RequirementSeed.model_fields
        }
    )
    validation_services.validate_requirements(requirements, subjects)
    return subjects, requirements


def snapshot_for(masters, code, *, earned=False, answers=False):
    subjects, requirements = masters
    curriculum = next(
        c for c in subjects.curricula if c.code == code + "-HANDBOOK-2026"
    )
    policy = next(
        p for p in requirements.completion_policies if p.curriculum_id == curriculum.id
    )
    return evaluation_models.EvaluationSnapshot(
        program_id=curriculum.program_id,
        curriculum_id=curriculum.id,
        data_revision=1,
        subjects=subjects,
        requirements=requirements,
        grades=[
            GradeAttempt(
                course_id=str(a.course_id),
                attempt_no=1,
                result_status="finalized",
                grade_code="A",
                academic_year=None,
                term_code=None,
            )
            for a in subjects.curriculum_courses
            if a.curriculum_id == curriculum.id
        ]
        if earned
        else [],
        completion_answers=[
            completion_policy.CompletionAnswer(code=c.code, status="met")
            for c in policy.non_credit_conditions
        ]
        if answers
        else [],
    )


def test_scope_and_official_totals(masters):
    subjects, requirements = masters
    assert len(subjects.curricula) == 38
    assert sum(not p.unresolved_reasons for p in requirements.completion_policies) == 28
    assert (
        len(
            {
                p.faculty_name
                for p in subjects.academic_programs
                if p.faculty_name.endswith("学部")
            }
        )
        == 6
    )
    assert (
        len(
            {
                p.faculty_name
                for p in subjects.academic_programs
                if p.faculty_name.endswith("研究科")
            }
        )
        == 4
    )
    # 公式卒業表: デザイン124、看護128/134、リハビリ/臨床検査128。
    expected = {
        "DS-VISUAL": 124,
        "HS-NS": 128,
        "HS-NS-PHN": 134,
        "HS-R-PT": 128,
        "HS-R-OT": 128,
        "HS-MT": 128,
    }
    for code, total in expected.items():
        s = snapshot_for(masters, code)
        r = next(
            r
            for r in requirements.graduation_requirements
            if r.curriculum_id == s.curriculum_id and r.kind == "total"
        )
        assert r.required_credits == total
    assert all(
        c.admission_year_from is None and c.verification_status == "unverified"
        for c in subjects.curricula
    )


def test_every_ready_bachelor_can_evaluate_empty_and_full_grades(masters):
    subjects, requirements = masters
    for policy in requirements.completion_policies:
        if policy.degree_level != "bachelor" or policy.unresolved_reasons:
            continue
        curriculum = next(c for c in subjects.curricula if c.id == policy.curriculum_id)
        code = curriculum.code.removesuffix("-HANDBOOK-2026")
        assert (
            evaluation_services.evaluate_graduation(snapshot_for(masters, code)).result
            == "fail"
        ), code
        assert (
            evaluation_services.evaluate_graduation(
                snapshot_for(masters, code, earned=True)
            ).result
            == "pass"
        ), code


@pytest.mark.parametrize(
    "code", ["GR-BIO-M", "GR-CS-M", "GR-MS-M", "GR-ES-M", "GR-DS-M", "GR-MT-M"]
)
def test_masters_require_credits_and_self_reported_noncredit_conditions(masters, code):
    pending = evaluation_services.evaluate_graduation(
        snapshot_for(masters, code, earned=True)
    )
    assert pending.result == "pending"
    assert pending.total.result == "pass"
    assert pending.total.required_credits == 30
    assert all(c.status == "unknown" for c in pending.completion_conditions)
    assert (
        evaluation_services.evaluate_graduation(
            snapshot_for(masters, code, earned=True, answers=True)
        ).result
        == "pass"
    )
    assert (
        evaluation_services.evaluate_graduation(
            snapshot_for(masters, code, answers=True)
        ).result
        == "fail"
    )
    s = snapshot_for(masters, code, earned=True, answers=True)
    s.completion_answers[0].status = "not_met"
    assert evaluation_services.evaluate_graduation(s).result == "fail"


def test_generic_skill_surplus_is_free_but_engineering_surplus_transfers(masters):
    for code, expected in [("GR-CS-M", 2), ("GR-ES-M", 4)]:
        result = evaluation_services.evaluate_graduation(
            snapshot_for(masters, code, earned=True, answers=True)
        )
        group = next(r for r in result.categories if r.required_credits == expected)
        assert group.earned_credits > group.credited_credits
        assert group.credited_credits == expected
    bio = evaluation_services.evaluate_graduation(
        snapshot_for(masters, "GR-CS-M", earned=True, answers=True)
    )
    es = evaluation_services.evaluate_graduation(
        snapshot_for(masters, "GR-ES-M", earned=True, answers=True)
    )
    assert bio.total.earned_credits - bio.total.credited_credits == 3
    assert es.total.earned_credits == es.total.credited_credits


def test_noncredit_conditions_follow_each_research_school(masters):
    conditions = {
        code: {
            c.code
            for c in next(
                p
                for p in masters[1].completion_policies
                if p.curriculum_id == snapshot_for(masters, code).curriculum_id
            ).non_credit_conditions
        }
        for code in ("GR-CS-M", "GR-ES-M", "GR-DS-M", "GR-MT-M")
    }
    assert (
        conditions["GR-CS-M"]
        == conditions["GR-ES-M"]
        == {"duration", "supervision", "thesis", "final_exam", "presentation"}
    )
    assert conditions["GR-DS-M"] == {"duration", "supervision", "thesis"}
    assert conditions["GR-MT-M"] == {"duration", "thesis", "final_exam"}


def test_missing_required_research_cannot_be_replaced_by_electives(masters):
    s = snapshot_for(masters, "GR-CS-M", earned=True, answers=True)
    policy = next(
        p
        for p in s.requirements.completion_policies
        if p.curriculum_id == s.curriculum_id
    )
    research = next(g for g in policy.credit_groups if g.required_course_ids)
    s.grades = [
        g for g in s.grades if g.course_id != str(research.required_course_ids[0])
    ]
    result = evaluation_services.evaluate_graduation(s)
    assert result.total.result == "pass"
    assert result.result == "fail"
    assert result.missing_required_courses


def test_incomplete_graduate_master_is_a_configuration_error(masters):
    s = snapshot_for(masters, "GR-CS-M", earned=True, answers=True).model_copy(
        deep=True
    )
    policy = next(
        p
        for p in s.requirements.completion_policies
        if p.curriculum_id == s.curriculum_id
    )
    policy.credit_groups.pop()
    with pytest.raises(evaluation.EvaluationError, match="invalid_evaluation_master"):
        evaluation_services.evaluate_graduation(s)


@pytest.mark.parametrize(
    "code",
    [
        "HS-CE",
        "HS-NS",
        "HS-NS-PHN",
        "GR-CS-D",
        "GR-BIO-D",
        "GR-MS-D",
        "GR-ES-D",
        "GR-BIO-M-EN",
        "GR-CS-M-EN",
        "GR-MS-M-EN",
    ],
)
def test_unverified_programs_stop_with_reason(masters, code):
    with pytest.raises(
        evaluation.EvaluationError, match="unverified_completion_policy"
    ):
        evaluation_services.evaluate_graduation(
            snapshot_for(masters, code, earned=True, answers=True)
        )


def test_speech_therapy_joint_electives_are_one_independent_minimum(masters):
    s = snapshot_for(masters, "HS-R-ST", earned=True)
    policy = next(
        p
        for p in s.requirements.completion_policies
        if p.curriculum_id == s.curriculum_id
    )
    minimum = policy.credit_minimums[0]
    names = {c.id: c.name for c in s.subjects.courses}
    assert {names[c] for c in minimum.course_ids} == {
        "生命倫理",
        "家族社会学",
        "文章表現リテラシー",
        "医療経済学",
        "公衆衛生学",
        "ケアマネジメント",
        "医療安全・人間工学概論",
        "先端医療総合講義",
        "生活環境福祉学",
    }
    s.grades = [
        g for g in s.grades if g.course_id not in {str(c) for c in minimum.course_ids}
    ]
    result = evaluation_services.evaluate_graduation(s)
    assert result.total.result == "pass"
    assert result.result == "fail"
    condition = next(r for r in result.requirements if r.code == minimum.code)
    assert condition.shortage == 3
    # 専門基礎から2＋専門発展から1で合計3を満たす。各区分で3ずつ要求しない。
    full = snapshot_for(masters, "HS-R-ST", earned=True)
    selected = {
        str(c) for c in minimum.course_ids if names[c] in {"生命倫理", "生活環境福祉学"}
    }
    s.grades += [g for g in full.grades if g.course_id in selected]
    assert evaluation_services.evaluate_graduation(s).result == "pass"


def test_foreign_or_duplicate_attestations_are_rejected(masters):
    s = snapshot_for(masters, "GR-CS-M", earned=True, answers=True)
    s.completion_answers.append(s.completion_answers[0])
    with pytest.raises(evaluation.EvaluationError, match="invalid_completion_answers"):
        evaluation_services.evaluate_graduation(s)
    with pytest.raises(ValidationError):
        check_results_dto.CheckRequest.model_validate(
            {
                "expected_revision": 1,
                "completion_answers": [{"code": "thesis", "status": True}],
            }
        )


def test_offline_regeneration_matches_checked_in_seeds(tmp_path):
    seed_directory = tmp_path / "seeds"
    seed_directory.mkdir()
    for name in (
        "build_university_seed.py",
        "university_external_rules.py",
        "university_2026.source.json",
        "cs_2026.json",
        "cs_requirements_2026.json",
    ):
        shutil.copyfile(SEEDS / name, seed_directory / name)
    subprocess.run(
        [sys.executable, "-m", "seeds.build_university_seed"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    for name in ("university_2026.json", "university_requirements_2026.json"):
        assert (seed_directory / name).read_bytes() == (SEEDS / name).read_bytes()
