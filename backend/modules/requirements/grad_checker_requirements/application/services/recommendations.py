"""既知の未修得科目を1科目ずつ試算し、不足が減る条件と理由をまとめる。"""

from collections.abc import Callable
from uuid import UUID

from modules.subjects.grad_checker_subjects.public import SubjectOfferingData

from ..dto.evaluation import (
    ConditionResult,
    CourseRecommendation,
    CourseResult,
    RecommendationReason,
)
from .evaluation_context import EvaluationContext


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
        reasons = [
            RecommendationReason(
                requirement_id=before.id,
                code=before.code,
                name=before.name,
                shortage_reduction=before.shortage - after.shortage,
                reason=f"{before.name}の不足を"
                f"{before.shortage - after.shortage}単位減らせる候補です。",
            )
            for before, after in zip(conditions, projected, strict=True)
            if before.shortage > after.shortage
        ]
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
