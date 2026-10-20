"""大学院の単位区分と本人申告の非単位条件を評価する。学部の換算を流用しない。"""

from uuid import NAMESPACE_URL, UUID, uuid5

from modules.grades.public import PASSING_GRADE_CODES, GradeError, check_attempts
from modules.requirements.application.dto.completion_policy import CompletionPolicyData
from modules.requirements.application.dto.evaluation import (
    CompletionConditionResult,
    ConditionResult,
    CourseResult,
    CreditSummary,
    EvaluationResult,
    EvaluationSnapshot,
)
from modules.requirements.application.errors.evaluation import EvaluationError
from modules.requirements.application.services.credit_summary import summarize


def evaluate_graduate(
    snapshot: EvaluationSnapshot, policy: CompletionPolicyData
) -> EvaluationResult:
    courses = {c.id: c for c in snapshot.subjects.courses}
    associations = {
        a.course_id: a
        for a in snapshot.subjects.curriculum_courses
        if a.curriculum_id == snapshot.curriculum_id
    }
    try:
        check_attempts(snapshot.grades)
    except GradeError as error:
        raise EvaluationError(
            error.code, "保存済み成績の履修回次が不正です。"
        ) from error
    latest = {}
    for grade in snapshot.grades:
        try:
            cid = UUID(grade.course_id)
        except ValueError as error:
            raise EvaluationError("invalid_grades", "科目IDが不正です。") from error
        if cid not in courses:
            raise EvaluationError("unknown_course", "未知の科目が含まれています。")
        if cid not in latest or latest[cid].attempt_no < grade.attempt_no:
            latest[cid] = grade
    earned = {
        cid
        for cid, g in latest.items()
        if g.result_status == "finalized" and g.grade_code in PASSING_GRADE_CODES
    }
    if earned - associations.keys():
        raise EvaluationError(
            "unsupported_external_credits",
            "他研究科・課程の科目の認定結果と算入規則が未確認です。",
        )

    def earned_credits(ids: set[UUID]) -> int:
        return sum(courses[c].credits for c in ids & earned)

    raw = {g.code: earned_credits(set(g.course_ids)) for g in policy.credit_groups}
    allocated = {
        g.code: min(raw[g.code], g.max_credits)
        if g.max_credits is not None
        else raw[g.code]
        for g in policy.credit_groups
    }
    # 算入先は原修得量から一度だけ計算し、連鎖換算や二重計上を行わない。
    for group in policy.credit_groups:
        if group.overflow_target is not None:
            allocated[group.overflow_target] += raw[group.code] - allocated[group.code]

    conditions = []
    for group in policy.credit_groups:
        result = ConditionResult(
            **summarize(
                group.required_credits, raw[group.code], allocated[group.code]
            ).model_dump(),
            id=uuid5(NAMESPACE_URL, f"{policy.id}:{group.code}"),
            code=group.code,
            name=group.name,
            kind="classification_total",
            parent_id=None,
            classification_id=associations[group.course_ids[0]].classification_id,
        )
        if not set(group.required_course_ids) <= earned:
            result.result = "fail"
        conditions.append(result)
    total = CreditSummary(
        **summarize(
            sum(g.required_credits for g in policy.credit_groups),
            earned_credits(set(associations)),
            sum(allocated.values()),
        ).model_dump()
    )
    answer_codes = [a.code for a in snapshot.completion_answers]
    known = {c.code for c in policy.non_credit_conditions}
    if len(set(answer_codes)) != len(answer_codes) or not set(answer_codes) <= known:
        raise EvaluationError(
            "invalid_completion_answers",
            "修了条件の回答が重複しているか、この課程の条件ではありません。",
        )
    answers = {a.code: a.status for a in snapshot.completion_answers}
    noncredits = [
        CompletionConditionResult(
            **c.model_dump(), status=answers.get(c.code, "unknown")
        )
        for c in policy.non_credit_conditions
    ]
    pending = any(c.status == "unknown" for c in noncredits)
    result = (
        "pending"
        if pending
        else "pass"
        if total.result == "pass"
        and all(c.result == "pass" for c in conditions)
        and all(c.status == "met" for c in noncredits)
        else "fail"
    )
    course_results = []
    required_ids = {cid for g in policy.credit_groups for cid in g.required_course_ids}
    for cid in sorted(associations.keys() | latest.keys(), key=str):
        grade = latest.get(cid)
        course_results.append(
            CourseResult(
                course_id=cid,
                name=courses[cid].name,
                classification_id=associations[cid].classification_id
                if cid in associations
                else None,
                credits=courses[cid].credits,
                status="earned"
                if cid in earned
                else "pending"
                if grade and grade.result_status == "pending"
                else "not_earned"
                if grade
                else "not_taken",
                latest_attempt=grade,
            )
        )
    return EvaluationResult(
        result=result,
        data_revision=snapshot.data_revision,
        curriculum=next(
            c for c in snapshot.subjects.curricula if c.id == snapshot.curriculum_id
        ),
        rule_revisions={policy.id: 1},
        total=total,
        categories=conditions,
        requirements=conditions,
        courses=course_results,
        missing_required_courses=[
            c
            for c in course_results
            if c.course_id in required_ids and c.status != "earned"
        ],
        allocations=[],
        external_allocations=[],
        warnings=[],
        recommendations=[],
        degree_level=policy.degree_level,
        completion_conditions=noncredits,
    )
