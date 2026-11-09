"""既知の未修得科目を1科目ずつ試算し、不足が減る条件と理由をまとめる。"""

from collections.abc import Callable
from uuid import UUID

from modules.requirements.application.dto.evaluation import (
    ConditionResult,
    CourseRecommendation,
    CourseResult,
    RecommendationReason,
)
from modules.requirements.application.services.evaluation_context import (
    EvaluationContext,
)
from modules.subjects.public import SubjectOfferingData


def shortage_reductions(
    before: list[ConditionResult], after: list[ConditionResult]
) -> list[RecommendationReason]:
    """同じ条件の不足をIDで比較し、試算結果の並び順には依存しない。"""
    projected = {row.id: row for row in after}
    before_ids = {row.id for row in before}
    if (
        len(before_ids) != len(before)
        or len(projected) != len(after)
        or before_ids != projected.keys()
    ):
        raise ValueError("推薦の試算前後で要件が一致しません。")
    reasons = []
    for condition in before:
        reduction = condition.shortage - projected[condition.id].shortage
        if reduction > 0:
            reasons.append(
                RecommendationReason(
                    requirement_id=condition.id,
                    code=condition.code,
                    name=condition.name,
                    shortage_reduction=reduction,
                    reason=f"{condition.name}の不足を{reduction}単位減らせる候補です。",
                )
            )
    return reasons


def recommend_courses(
    context: EvaluationContext,
    courses: list[CourseResult],
    conditions: list[ConditionResult],
    project: Callable[[UUID], list[ConditionResult] | None],
) -> list[CourseRecommendation]:
    if not any(row.shortage for row in conditions):
        return []
    known = {row.course_id: row for row in courses}
    external_ids: set[UUID] = set()
    # 所属課程外は明示的な対応表と確認済み規則が揃った科目だけを試算する。
    for mapping in context.snapshot.requirements.credit_rule_courses:
        rule = context.rules.get(mapping.rule_id)
        if (
            mapping.curriculum_id == context.curriculum.id
            and rule is not None
            and rule.kind == "other_faculty"
            and rule.verification_status == "verified"
            and mapping.course_id not in context.associations
        ):
            external_ids.add(mapping.course_id)
            course = context.courses[mapping.course_id]
            known.setdefault(
                course.id,
                CourseResult(
                    course_id=course.id,
                    name=course.name,
                    credits=course.credits,
                    classification_id=None,
                    status="not_taken",
                    latest_attempt=None,
                ),
            )
    offerings: dict[UUID, list[SubjectOfferingData]] = {}
    for offering in context.snapshot.subjects.course_offerings:
        offerings.setdefault(offering.course_id, []).append(offering)
    recommendations = []
    for course_id, course in known.items():
        if course.status == "earned" or (
            course_id not in context.associations and course_id not in external_ids
        ):
            continue
        projected = project(course_id)
        if projected is None:
            continue
        reasons = shortage_reductions(conditions, projected)
        if not reasons:
            continue
        association = context.associations.get(course_id)
        course_offerings = sorted(
            offerings.get(course_id, []),
            key=lambda row: (row.semester_order, row.term_code, row.academic_year or 0),
        )
        recommendations.append(
            CourseRecommendation(
                **course.model_dump(),
                is_required=association is not None
                and association.course_type == "required",
                offerings=course_offerings,
                contributions=reasons,
            )
        )
    return sorted(
        recommendations,
        key=lambda row: (
            not row.is_required,
            min((term.semester_order for term in row.offerings), default=float("inf")),
            str(row.course_id),
        ),
    )
