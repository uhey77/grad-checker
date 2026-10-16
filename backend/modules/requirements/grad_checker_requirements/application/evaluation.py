"""卒業単位条件の共通計算。副作用を持たず、未確認事項をfailに読み替えない。"""

from collections import defaultdict
from uuid import UUID

from pydantic import ValidationError

from modules.grades.grad_checker_grades.domain.grade import PASSING_GRADE_CODES
from modules.requirements.grad_checker_requirements.domain.requirement import (
    CreditRuleKind,
    RequirementKind,
)

from .errors.evaluation import (
    EvaluationError,
)
from .evaluation_context import (
    EvaluationContext,
    invalid_master,
)
from .evaluation_models import (
    ConditionResult,
    CourseResult,
    CreditSummary,
    EvaluationResult,
    EvaluationSnapshot,
    OverflowAllocation,
)
from .seed import (
    RequirementData,
)


def summarize(required: int, earned: int, credited: int) -> CreditSummary:
    shortage = max(required - credited, 0)
    return CreditSummary(
        required_credits=required,
        earned_credits=earned,
        credited_credits=credited,
        shortage=shortage,
        result="fail" if shortage else "pass",
    )


class _Evaluation:
    def __init__(self, context: EvaluationContext) -> None:
        self.context = context
        self.earned = {
            course_id
            for course_id, grade in context.latest.items()
            if grade.result_status == "finalized"
            and grade.grade_code in PASSING_GRADE_CODES
        }
        self.elective: dict[UUID, int] = defaultdict(int)
        self.credited: dict[UUID, int] = defaultdict(int)
        self.group_credits: dict[UUID, int] = {}
        self.allocations: list[OverflowAllocation] = []

    def credits(self, ids: set[UUID]) -> int:
        return sum(self.context.courses[key].credits for key in ids & self.earned)

    def reject_external_credits(self) -> None:
        # 他学部の対象照合・上限配分は後続の実装。実単位を黙って除外しない。
        if not self.earned - self.context.associations.keys():
            return
        for rule in self.context.rules.values():
            if rule.kind == CreditRuleKind.OTHER_FACULTY and rule.unresolved_reason:
                raise EvaluationError(
                    "unverified_credit_rule", rule.unresolved_reason, rule_id=rule.id
                )
        raise EvaluationError(
            "unsupported_external_credits",
            "本人課程外の修得科目の算入には、対象照合と他学部算入処理が必要です。",
        )

    def allocate(self) -> None:
        context = self.context
        self.reject_external_credits()
        for course_id in self.earned:
            association = context.associations[course_id]
            root = context.root(association.classification_id)
            credit_value = context.courses[course_id].credits
            if association.course_type == "required":
                self.credited[root] += credit_value
            elif association.course_type == "elective":
                self.elective[root] += credit_value
                self.credited[root] += credit_value
        for condition in context.conditions:
            if condition.kind != RequirementKind.SELECTIVE_GROUP:
                continue
            assert condition.classification_id is not None
            root = context.root(condition.classification_id)
            earned = self.credits(context.targets[condition.id])
            group = min(earned, condition.required_credits)
            self.group_credits[condition.id] = group
            self.credited[root] += group
            overflow = earned - group
            if overflow:
                allocation = self.overflow(condition, earned, group, root)
                self.allocations.append(allocation)
                self.elective[root] += allocation.transferred_credits
                self.credited[root] += allocation.transferred_credits

    def overflow(
        self, condition: RequirementData, earned: int, group: int, root: UUID
    ) -> OverflowAllocation:
        context = self.context
        targets = context.targets[condition.id]
        mappings = [
            row
            for row in context.snapshot.requirements.credit_rule_courses
            if row.curriculum_id == context.curriculum.id
            and row.course_id in targets
            and context.rules[row.rule_id].kind == CreditRuleKind.SELECTIVE_OVERFLOW
        ]
        if (
            {row.course_id for row in mappings} != targets
            or len({row.rule_id for row in mappings}) != 1
            or {row.target_classification_id for row in mappings} != {root}
        ):
            raise invalid_master("選択必修群の超過換算規則が不足または不整合です。")
        rule = context.rules[mappings[0].rule_id]
        if rule.verification_status != "verified":
            raise EvaluationError(
                "unverified_credit_rule",
                rule.unresolved_reason or "超過換算規則が未確認です。",
                rule_id=rule.id,
            )
        if any(
            child.kind == RequirementKind.SUBMINIMUM
            and child.parent_id == condition.id
            and self.credits(context.targets[child.id]) < child.required_credits
            for child in context.conditions
        ):
            raise EvaluationError(
                "unresolved_allocation",
                "内訳条件が不足する群の超過換算方法が未確定です。",
                rule_id=rule.id,
            )
        return OverflowAllocation(
            rule_id=rule.id,
            requirement_id=condition.id,
            target_classification_id=root,
            earned_credits=earned,
            group_credits=group,
            overflow_credits=earned - group,
            transferred_credits=earned - group,
        )

    def condition_result(self, condition: RequirementData) -> ConditionResult:
        context = self.context
        earned = self.credits(context.targets[condition.id])
        credited = earned
        if condition.kind == RequirementKind.TOTAL:
            credited = sum(self.credited.values())
        elif condition.kind == RequirementKind.CLASSIFICATION_TOTAL:
            assert condition.classification_id is not None
            credited = self.credited[condition.classification_id]
        elif condition.kind == RequirementKind.ELECTIVE_TOTAL:
            assert condition.classification_id is not None
            credited = self.elective[condition.classification_id]
            # 選択条件の分類集合は算入先。区分全体の修得単位を再掲しない。
            earned = self.credits(
                {
                    key
                    for key in context.targets[condition.id]
                    if context.associations[key].course_type == "elective"
                }
            )
        elif condition.kind == RequirementKind.SELECTIVE_GROUP:
            credited = self.group_credits[condition.id]
        return ConditionResult(
            **summarize(condition.required_credits, earned, credited).model_dump(),
            id=condition.id,
            code=condition.code,
            name=condition.name,
            kind=condition.kind,
            parent_id=condition.parent_id,
            classification_id=condition.classification_id,
        )

    def course_result(self, course_id: UUID) -> CourseResult:
        context = self.context
        course = context.courses[course_id]
        attempt = context.latest.get(course_id)
        association = context.associations.get(course_id)
        result = CourseResult(
            course_id=course_id,
            name=course.name,
            credits=course.credits,
            classification_id=association.classification_id if association else None,
            status="not_taken",
            latest_attempt=attempt,
        )
        if course_id in self.earned:
            result.status = "earned"
        elif attempt is not None:
            result.status = (
                "pending" if attempt.result_status == "pending" else "not_earned"
            )
        return result

    def run(self) -> EvaluationResult:
        self.allocate()
        context = self.context
        conditions = [self.condition_result(row) for row in context.conditions]
        total = next(row for row in conditions if row.kind == RequirementKind.TOTAL)
        courses = [
            self.course_result(key)
            for key in sorted(
                context.associations.keys() | context.latest.keys(), key=str
            )
        ]
        missing = [
            row
            for row in courses
            if row.course_id in context.associations
            and context.associations[row.course_id].course_type == "required"
            and row.status != "earned"
        ]
        return EvaluationResult(
            result="pass"
            if all(row.result == "pass" for row in conditions)
            else "fail",
            data_revision=context.snapshot.data_revision,
            curriculum=context.curriculum,
            rule_revisions={key: row.revision for key, row in context.rules.items()},
            total=CreditSummary(
                **total.model_dump(include=set(CreditSummary.model_fields))
            ),
            categories=[
                r for r in conditions if r.kind == RequirementKind.CLASSIFICATION_TOTAL
            ],
            requirements=conditions,
            courses=courses,
            missing_required_courses=missing,
            allocations=self.allocations,
        )


def evaluate_graduation(snapshot: EvaluationSnapshot) -> EvaluationResult:
    """検証済みの独立コピーで計算し、正常結果か理由付き業務エラーを返す。

    入力を変更せず、履歴保存・時刻採番・DB読取・推薦・他学部算入は行わない。
    """
    try:
        validated = EvaluationSnapshot.model_validate(
            snapshot.model_dump(warnings=False)
        )
    except ValidationError as error:
        raise EvaluationError(
            "invalid_evaluation_input", "判定入力の形式が不正です。"
        ) from error
    return _Evaluation(EvaluationContext(validated)).run()
