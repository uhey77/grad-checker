"""明示的に照合済みの他学部科目を、取得順・同時期の不足条件に従って算入する。"""

from collections import defaultdict
from uuid import UUID

from ..domain.credits import AllocationTarget, CreditRequirement, allocate_best_fit
from .errors.evaluation import EvaluationError
from .evaluation_context import EvaluationContext, invalid_master
from .evaluation_models import EvaluationWarning, ExternalAllocation


def allocate_external(
    context: EvaluationContext,
    earned: set[UUID],
    credited: dict[UUID, int],
    elective: dict[UUID, int],
) -> tuple[list[ExternalAllocation], list[EvaluationWarning]]:
    external = earned - context.associations.keys()
    if not external:
        return [], []
    mappings = {
        row.course_id: row
        for row in context.snapshot.requirements.credit_rule_courses
        if row.curriculum_id == context.curriculum.id
        and context.rules[row.rule_id].kind == "other_faculty"
    }
    if not external <= mappings.keys():
        raise EvaluationError(
            "unsupported_external_credits", "所属課程外の科目の算入先が未登録です。"
        )
    rule_ids = {mappings[key].rule_id for key in external}
    if len(rule_ids) != 1:
        raise invalid_master("他学部科目の共通上限を一つにまとめてください。")
    rule_id = next(iter(rule_ids))
    rule = context.rules[rule_id]
    if rule.allocation_policy != "chronological_best_fit_v1":
        raise EvaluationError(
            "unverified_credit_rule",
            "他学部科目の配分方針が設定されていません。",
            rule_id=rule_id,
        )
    limit = next(
        row.max_credits
        for row in context.snapshot.requirements.credit_rule_limits
        if row.rule_id == rule_id
    )
    targets = {key: mappings[key].target_classification_id for key in external}
    totals: dict[UUID, int] = defaultdict(int)
    for key in external:
        totals[targets[key]] += context.courses[key].credits
    total = sum(totals.values())
    allocated: dict[UUID, int] = defaultdict(int)
    warnings: list[EvaluationWarning] = []
    if total <= limit:
        allocated.update(totals)
    elif len(totals) == 1:
        allocated[next(iter(totals))] = limit
    else:
        allocated.update(
            chronological_allocation(context, targets, limit, credited, elective)
        )
        warnings.append("provisional_external_allocation")
    return [
        ExternalAllocation(
            rule_id=rule_id,
            target_classification_id=root,
            target_name=context.classes[root].name,
            earned_credits=totals[root],
            credited_credits=allocated[root],
            free_credits=totals[root] - allocated[root],
        )
        for root in sorted(totals, key=str)
    ], warnings


def chronological_allocation(
    context: EvaluationContext,
    targets: dict[UUID, UUID],
    limit: int,
    credited: dict[UUID, int],
    elective: dict[UUID, int],
) -> dict[UUID, int]:
    # 日付欠落は最早・最遅の範囲として扱う。上限内に必ず入る／必ず外れる
    # 科目や、残りの算入先が一つだけの場合には入力を要求しない。
    bounds = {}
    for key in targets:
        grade = context.latest[key]
        first = 0 if grade.term_code != "second" else 1
        last = 1 if grade.term_code != "first" else 0
        bounds[key] = (
            (grade.academic_year or 1900) * 2 + first,
            (grade.academic_year or 2100) * 2 + last,
        )
    allocated: dict[UUID, int] = defaultdict(int)
    undecided = set()
    for key, (start, end) in bounds.items():
        possible_before = sum(
            context.courses[k].credits for k, (lo, _) in bounds.items() if lo <= end
        )
        certain_before = sum(
            context.courses[k].credits for k, (_, hi) in bounds.items() if hi < start
        )
        if possible_before <= limit:
            allocated[targets[key]] += context.courses[key].credits
        elif certain_before < limit:
            undecided.add(key)
    remaining = limit - sum(allocated.values())
    roots = {targets[key] for key in undecided}
    if len(roots) == 1:
        allocated[next(iter(roots))] += remaining
        return allocated
    if any(bounds[key][0] != bounds[key][1] for key in undecided):
        raise EvaluationError(
            "external_acquisition_period_required",
            "他学部科目の配分に取得時期が必要です。履修年度・学期を入力してください。",
        )
    cohorts: dict[int, dict[UUID, int]] = {}
    for key in undecided:
        cohort = cohorts.setdefault(bounds[key][0], defaultdict(int))
        cohort[targets[key]] += context.courses[key].credits
    for period in sorted(cohorts):
        if not remaining:
            break
        cohort = cohorts[period]
        if sum(cohort.values()) <= remaining:
            selected = cohort
        else:
            selected = best_fit(
                context, cohort, remaining, credited, elective, allocated=allocated
            )
        for root, value in selected.items():
            allocated[root] += value
            remaining -= value
    return allocated


def best_fit(
    context: EvaluationContext,
    cohort: dict[UUID, int],
    limit: int,
    credited: dict[UUID, int],
    elective: dict[UUID, int],
    *,
    allocated: dict[UUID, int],
) -> dict[UUID, int]:
    # DTOと現在までの算入量をDomainの配分条件へ変換する。
    targets = [
        AllocationTarget(
            id=root,
            code=context.classes[root].code,
            available_credits=available,
            conditions=tuple(
                CreditRequirement(
                    required=row.required_credits,
                    credited=(
                        credited if row.kind == "classification_total" else elective
                    ).get(root, 0)
                    + allocated.get(root, 0),
                )
                for row in context.conditions
                if row.classification_id == root
                and row.kind in ("classification_total", "elective_total")
            ),
        )
        for root, available in cohort.items()
    ]
    return allocate_best_fit(targets, limit)
