"""既存の必修条件の表示用内訳。判定条件・総単位には追加しない。"""

from collections import defaultdict
from uuid import NAMESPACE_URL, UUID, uuid5

from modules.requirements.application.dto.evaluation import (
    ConditionResult,
    EvaluationResult,
    EvaluationSnapshot,
)
from modules.requirements.application.services.credit_summary import summarize
from modules.requirements.application.services.validation import inside
from modules.requirements.domain.value_objects.requirement import RequirementKind


def required_course_breakdowns(
    snapshot: EvaluationSnapshot, result: EvaluationResult
) -> list[ConditionResult]:
    classes = {row.id: row for row in snapshot.subjects.classifications}
    courses = {row.course_id: row for row in result.courses}
    associations = [
        row
        for row in snapshot.subjects.curriculum_courses
        if row.curriculum_id == snapshot.curriculum_id and row.course_type == "required"
    ]
    breakdowns = []
    for condition in result.requirements:
        if (
            condition.kind != RequirementKind.REQUIRED_COURSES
            or condition.classification_id is None
            or condition.parent_id is None
        ):
            continue
        groups: dict[UUID, list[UUID]] = defaultdict(list)
        for association in associations:
            classification_id = association.classification_id
            if classification_id != condition.classification_id and inside(
                classes, classification_id, condition.classification_id
            ):
                groups[classification_id].append(association.course_id)
        for classification_id in sorted(
            groups, key=lambda key: (classes[key].display_order, str(key))
        ):
            classification = classes[classification_id]
            required = sum(courses[key].credits for key in groups[classification_id])
            earned = sum(
                courses[key].credits
                for key in groups[classification_id]
                if courses[key].status == "earned"
            )
            breakdowns.append(
                ConditionResult(
                    **summarize(required, earned, earned).model_dump(),
                    id=uuid5(
                        NAMESPACE_URL,
                        f"required-breakdown:{condition.id}:{classification_id}",
                    ),
                    code=f"{classification.code}.required_breakdown",
                    name=f"{classification.name}の必修",
                    kind=RequirementKind.REQUIRED_COURSES,
                    parent_id=condition.parent_id,
                    classification_id=classification_id,
                )
            )
    return breakdowns
