"""推薦の優先順、実際の算入効果、未確認事項と保存互換を検証する。"""

# ruff: noqa: F811

import pytest
from test_external_allocation import add_external, external_snapshot  # noqa: F401
from test_requirement_evaluation import grade, snapshot, uid  # noqa: F401

from modules.requirements.grad_checker_requirements.application.evaluation import (
    evaluate_graduation,
)
from modules.subjects.grad_checker_subjects.application.subject_data_validation import (
    SubjectOfferingData,
)


def recommendations(sample):
    rows = evaluate_graduation(sample).recommendations
    assert rows is not None
    return rows


def test_required_first_then_earliest_semester_id_and_unknown_last(snapshot):
    snapshot.subjects.course_offerings = [
        SubjectOfferingData(course_id=uid(i), term_code=term, semester_order=order)
        for i, term, order in [
            (10, "second", 8),
            (11, "second", 2),
            (12, "first", 1),
            (12, "second", 4),
            (13, "first", 1),
            (14, "second", 2),
        ]
    ]
    before = snapshot.model_dump_json()
    rows = recommendations(snapshot)
    assert [row.course_id for row in rows] == [uid(i) for i in (10, 12, 13, 11, 14, 15)]
    assert rows[0].is_required
    assert not any(row.is_required for row in rows[1:])
    assert rows[1].offerings[0].semester_order == 1
    assert rows[-1].offerings == []
    snapshot.subjects.courses.reverse()
    snapshot.subjects.curriculum_courses.reverse()
    snapshot.subjects.course_offerings.reverse()
    assert recommendations(snapshot) == rows
    snapshot.subjects.courses.reverse()
    snapshot.subjects.curriculum_courses.reverse()
    snapshot.subjects.course_offerings.reverse()
    assert snapshot.model_dump_json() == before


def test_deduplicates_contributions_excludes_earned_and_preserves_status(snapshot):
    snapshot.grades = [grade(uid(10)), grade(uid(11), "D"), grade(uid(12), None)]
    rows = {row.course_id: row for row in recommendations(snapshot)}
    assert uid(10) not in rows
    assert rows[uid(11)].status == "not_earned"
    assert rows[uid(12)].status == "pending"
    assert rows[uid(14)].status == "not_taken"
    assert {row.code for row in rows[uid(11)].contributions} == {
        "r20",
        "r21",
        "r23",
        "r24",
    }
    assert all(
        row.shortage_reduction == 2 and row.reason
        for row in rows[uid(11)].contributions
    )


def test_no_shortages_means_no_recommendations(snapshot):
    snapshot.grades = [grade(uid(i)) for i in (10, 11, 13, 15)]
    assert recommendations(snapshot) == []


def test_full_group_recommends_overflow_only_if_verified(snapshot):
    snapshot.grades = [grade(uid(11))]
    rows = {row.course_id: row for row in recommendations(snapshot)}
    assert {reason.code for reason in rows[uid(12)].contributions} == {
        "r20",
        "r21",
        "r26",
    }
    rule = snapshot.requirements.credit_rules[0]
    rule.verification_status = "unverified"
    rule.unresolved_reason = "換算未確認"
    rows = {row.course_id: row for row in recommendations(snapshot)}
    assert uid(12) not in rows
    assert uid(10) in rows  # 確認済みの直接算入は提示できる。


def test_unmapped_courses_do_not_become_candidates(snapshot):
    snapshot.subjects.curriculum_courses.pop()
    assert uid(15) not in {row.course_id for row in recommendations(snapshot)}


def test_external_candidates_need_verified_mapping_and_available_cap(external_snapshot):
    sample = external_snapshot
    assert all(row.course_id.int < 100 for row in recommendations(sample))
    sample.requirements.credit_rules[-1].verification_status = "verified"
    sample.requirements.credit_rules[-1].unresolved_reason = None
    rows = {row.course_id: row for row in recommendations(sample)}
    assert {uid(i) for i in (100, 101, 102, 103)} <= rows.keys()
    assert {r.code for r in rows[uid(102)].contributions} == {"r20", "r40", "r41"}
    add_external(sample, (100, 101, 102), year=2026, term="first")
    # 共通上限を使い切った後、未知の取得時期で配分改善を断定しない。
    assert all(row.course_id.int < 100 for row in recommendations(sample))


def test_external_uncertain_acquisition_period_is_not_assumed(external_snapshot):
    sample = external_snapshot
    rule = sample.requirements.credit_rules[-1]
    rule.verification_status = "verified"
    rule.unresolved_reason = None
    add_external(sample, (100, 101, 102), year=2026, term="first")
    assert uid(103) not in {row.course_id for row in recommendations(sample)}


@pytest.mark.parametrize("code,status", [("X", "not_earned"), (None, "pending")])
def test_latest_retake_state_is_kept(snapshot, code, status):
    snapshot.grades = [grade(uid(10), "D"), grade(uid(10), code, attempt=2)]
    row = recommendations(snapshot)[0]
    assert row.status == status and row.latest_attempt.attempt_no == 2
