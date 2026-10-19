"""科目マスタと要件集合の参照・階層・対象集合・規則の整合性検証。"""

from collections import defaultdict
from collections.abc import Callable, Iterable
from uuid import UUID

from modules.requirements.grad_checker_requirements.application.errors.seed import (
    RequirementSeedError,
)
from modules.requirements.grad_checker_requirements.application.seed import (
    RequirementData,
    RequirementSeed,
)
from modules.requirements.grad_checker_requirements.domain.requirement import (
    CreditRuleKind,
    RequirementKind,
)
from modules.subjects.grad_checker_subjects.application.errors.subject_data import (
    SeedError,
)
from modules.subjects.grad_checker_subjects.application.subject_data_validation import (
    ClassificationData,
    SubjectDataSeed,
    validate_subject_data,
)


def unique[T, K](records: Iterable[T], key: Callable[[T], K], label: str) -> dict[K, T]:
    result: dict[K, T] = {}
    for record in records:
        identity = key(record)
        if identity in result:
            raise RequirementSeedError(f"{label}が重複しています。")
        result[identity] = record
    return result


def inside(
    classes: dict[UUID, ClassificationData], child_id: UUID, ancestor_id: UUID
) -> bool:
    visited: set[UUID] = set()
    current: UUID | None = child_id
    while current is not None and current not in visited:
        if current == ancestor_id:
            return True
        visited.add(current)
        current = classes[current].parent_id
    return False


def same_class(
    classes: dict[UUID, ClassificationData],
    curriculum_id: UUID,
    classification_id: UUID,
) -> None:
    if (
        classification_id not in classes
        or classes[classification_id].curriculum_id != curriculum_id
    ):
        raise RequirementSeedError("分類は同じカリキュラム内で指定してください。")


def validate_requirements(
    seed: RequirementSeed, subjects: SubjectDataSeed
) -> list[RequirementData]:
    """既存分と追加分を合わせて検証し、要件を親から順に返す。"""
    try:
        validate_subject_data(subjects)
    except SeedError as error:
        raise RequirementSeedError("科目マスタが不整合です: " + str(error)) from error
    curricula = {row.id for row in subjects.curricula}
    classes = {row.id: row for row in subjects.classifications}
    requirements = unique(seed.graduation_requirements, lambda x: x.id, "要件ID")
    unique(
        seed.graduation_requirements, lambda x: (x.curriculum_id, x.code), "要件コード"
    )
    unique(seed.requirement_scopes, lambda x: x.id, "対象集合ID")
    unique(
        seed.requirement_scopes,
        lambda x: (x.requirement_id, x.classification_id, x.course_id),
        "要件の対象",
    )

    for requirement in requirements.values():
        if requirement.curriculum_id not in curricula:
            raise RequirementSeedError("要件のカリキュラムが存在しません。")
        if requirement.kind == RequirementKind.TOTAL:
            if (
                requirement.parent_id is not None
                or requirement.classification_id is not None
            ):
                raise RequirementSeedError("総単位条件には親・分類を指定できません。")
        else:
            if requirement.classification_id is None:
                raise RequirementSeedError("総単位以外の条件には分類が必要です。")
            same_class(
                classes, requirement.curriculum_id, requirement.classification_id
            )
            parent = requirements.get(requirement.parent_id)
            if parent is None or parent.curriculum_id != requirement.curriculum_id:
                raise RequirementSeedError(
                    "親要件は同じカリキュラム内で指定してください。"
                )
            expected_parent = {
                RequirementKind.CLASSIFICATION_TOTAL: RequirementKind.TOTAL,
                RequirementKind.SUBMINIMUM: RequirementKind.SELECTIVE_GROUP,
            }.get(requirement.kind, RequirementKind.CLASSIFICATION_TOTAL)
            if parent.kind != expected_parent:
                raise RequirementSeedError(
                    "要件の親子の種類が不正です。循環は許可しません。"
                )
            if parent.classification_id is not None and not inside(
                classes, requirement.classification_id, parent.classification_id
            ):
                raise RequirementSeedError(
                    "子要件の分類が親要件の分類に含まれていません。"
                )

    unique(
        (x for x in requirements.values() if x.kind == RequirementKind.TOTAL),
        lambda x: x.curriculum_id,
        "カリキュラムの総単位条件",
    )
    remaining = dict(requirements)
    ordered: list[RequirementData] = []
    visited: set[UUID] = set()
    while remaining:
        ready = [
            x
            for x in remaining.values()
            if x.parent_id is None or x.parent_id in visited
        ]
        if not ready:
            raise RequirementSeedError("要件の親子関係が循環しています。")
        for row in ready:
            ordered.append(row)
            visited.add(row.id)
            del remaining[row.id]

    validate_targets(seed, subjects, ordered)
    validate_rules(seed, subjects)
    validate_completion_policies(seed, subjects)
    return ordered


def validate_targets(
    seed: RequirementSeed, subjects: SubjectDataSeed, ordered: list[RequirementData]
) -> None:
    requirements = {row.id: row for row in ordered}
    classes = {row.id: row for row in subjects.classifications}
    courses = {row.id: row for row in subjects.courses}
    associations = {
        (row.curriculum_id, row.course_id): row for row in subjects.curriculum_courses
    }
    targets: dict[UUID, set[UUID]] = defaultdict(set)
    for scope in seed.requirement_scopes:
        requirement = requirements.get(scope.requirement_id)
        if requirement is None or scope.curriculum_id != requirement.curriculum_id:
            raise RequirementSeedError(
                "対象集合の要件が存在しないか課程が一致しません。"
            )
        if scope.classification_id is not None:
            same_class(classes, scope.curriculum_id, scope.classification_id)
            candidates = {
                row.course_id
                for row in subjects.curriculum_courses
                if row.curriculum_id == scope.curriculum_id
                and inside(classes, row.classification_id, scope.classification_id)
            }
        else:
            if (scope.curriculum_id, scope.course_id) not in associations:
                raise RequirementSeedError("要件の対象科目は本人課程の科目に限ります。")
            assert scope.course_id is not None
            candidates = {scope.course_id}
        if targets[requirement.id] & candidates:
            raise RequirementSeedError("同じ要件内の対象集合が重複しています。")
        targets[requirement.id].update(candidates)

    selective: dict[UUID, set[UUID]] = defaultdict(set)
    for row in ordered:
        selected = targets[row.id]
        if not selected:
            raise RequirementSeedError("要件の対象集合が空です。")
        if row.parent_id is not None and not selected <= targets[row.parent_id]:
            raise RequirementSeedError("子要件の対象は親要件の対象に含めてください。")
        if row.classification_id is not None and any(
            not inside(
                classes,
                associations[row.curriculum_id, course].classification_id,
                row.classification_id,
            )
            for course in selected
        ):
            raise RequirementSeedError("対象科目が要件の分類外です。")
        course_type = {
            RequirementKind.REQUIRED_COURSES: "required",
            RequirementKind.SELECTIVE_GROUP: "selective",
            RequirementKind.SUBMINIMUM: "selective",
        }.get(row.kind)
        if course_type and any(
            associations[row.curriculum_id, course].course_type != course_type
            for course in selected
        ):
            raise RequirementSeedError("要件の種類と対象科目の種別が一致しません。")
        credit_total = sum(courses[course].credits for course in selected)
        if row.kind == RequirementKind.REQUIRED_COURSES:
            expected = {
                item.course_id
                for item in subjects.curriculum_courses
                if item.curriculum_id == row.curriculum_id
                and item.course_type == "required"
                and row.classification_id is not None
                and inside(classes, item.classification_id, row.classification_id)
            }
            if selected != expected or credit_total != row.required_credits:
                raise RequirementSeedError(
                    "必修集合・必修単位数が科目マスタと一致しません。"
                )
        if course_type and credit_total < row.required_credits:
            raise RequirementSeedError("対象科目の単位数が必要単位数に足りません。")
        if row.kind == RequirementKind.SELECTIVE_GROUP:
            if selective[row.curriculum_id] & selected:
                raise RequirementSeedError(
                    "独立した選択必修群の対象科目が重複しています。"
                )
            selective[row.curriculum_id].update(selected)


def validate_rules(seed: RequirementSeed, subjects: SubjectDataSeed) -> None:
    curricula = {row.id for row in subjects.curricula}
    classes = {row.id: row for row in subjects.classifications}
    courses = {row.id for row in subjects.courses}
    associations = {
        (x.curriculum_id, x.course_id): x for x in subjects.curriculum_courses
    }
    rules = unique(seed.credit_rules, lambda x: x.id, "規則ID")
    unique(
        (row for row in seed.credit_rules if row.kind == CreditRuleKind.OTHER_FACULTY),
        lambda row: row.curriculum_id,
        "課程の他学部共通上限規則",
    )
    unique(seed.credit_rules, lambda x: (x.curriculum_id, x.code), "規則コード")
    unique(
        seed.credit_rule_courses, lambda x: (x.rule_id, x.course_id), "規則の対象科目"
    )
    unique(seed.credit_rule_limits, lambda x: x.id, "上限ID")
    unique(
        seed.credit_rule_limits, lambda x: (x.rule_id, x.limit_group_code), "共通上限"
    )
    mapped: dict[UUID, set[UUID]] = defaultdict(set)
    allocations: set[tuple[UUID, CreditRuleKind, UUID]] = set()
    for row in seed.credit_rule_courses:
        rule = rules.get(row.rule_id)
        target = classes.get(row.target_classification_id)
        if rule is None or rule.curriculum_id != row.curriculum_id:
            raise RequirementSeedError("算入規則が存在しないか課程が一致しません。")
        if (
            target is None
            or target.curriculum_id != row.curriculum_id
            or target.parent_id is not None
        ):
            raise RequirementSeedError(
                "算入先は同じカリキュラムの最上位分類を指定してください。"
            )
        if row.course_id not in courses:
            raise RequirementSeedError("算入規則の対象科目が存在しません。")
        if rule.kind == CreditRuleKind.OTHER_FACULTY:
            if (row.curriculum_id, row.course_id) in associations:
                raise RequirementSeedError(
                    "他学部算入の対象に本人課程の科目は指定できません。"
                )
            if (
                next(x for x in subjects.courses if x.id == row.course_id).teaching_type
                != "lecture"
            ):
                raise RequirementSeedError(
                    "他学部算入の対象は照合済みの講義科目に限ります。"
                )
        key = (row.curriculum_id, rule.kind, row.course_id)
        if key in allocations:
            raise RequirementSeedError(
                "同じ種類の規則で対象科目の配分が重複しています。"
            )
        allocations.add(key)
        if rule.kind == CreditRuleKind.SELECTIVE_OVERFLOW:
            association = associations.get((row.curriculum_id, row.course_id))
            if association is None or association.course_type != "selective":
                raise RequirementSeedError(
                    "超過換算の対象は本人課程の選択必修科目です。"
                )
            current = classes[association.classification_id]
            while current.parent_id is not None:
                current = classes[current.parent_id]
            if current.id != target.id:
                raise RequirementSeedError(
                    "選択必修の超過換算は同じ科目区分に限ります。"
                )
        mapped[rule.id].add(row.course_id)
    limits: dict[UUID, int] = defaultdict(int)
    for limit in seed.credit_rule_limits:
        rule = rules.get(limit.rule_id)
        if rule is None or rule.kind != CreditRuleKind.OTHER_FACULTY:
            raise RequirementSeedError("共通上限は他学部算入規則に指定してください。")
        limits[rule.id] += 1
    for rule in rules.values():
        if rule.curriculum_id not in curricula:
            raise RequirementSeedError("規則のカリキュラムが存在しません。")
        if rule.kind == CreditRuleKind.OTHER_FACULTY and limits[rule.id] != 1:
            raise RequirementSeedError(
                "他学部算入には算入先をまたぐ共通上限が1つ必要です。"
            )
        if not mapped[rule.id] and (
            rule.kind == CreditRuleKind.SELECTIVE_OVERFLOW
            or rule.verification_status == "verified"
        ):
            raise RequirementSeedError("この規則には明示的な対象科目が必要です。")


def validate_completion_policies(
    seed: RequirementSeed, subjects: SubjectDataSeed
) -> None:
    unique(seed.completion_policies, lambda row: row.id, "修了規則ID")
    unique(seed.completion_policies, lambda row: row.curriculum_id, "課程の修了規則")
    curricula = {row.id for row in subjects.curricula}
    courses = {row.id: row for row in subjects.courses}
    for policy in seed.completion_policies:
        if policy.curriculum_id not in curricula:
            raise RequirementSeedError("修了規則の課程が存在しません。")
        associated = {
            row.course_id
            for row in subjects.curriculum_courses
            if row.curriculum_id == policy.curriculum_id
        }
        covered = set()
        for minimum in policy.credit_minimums:
            if (
                not set(minimum.course_ids) <= associated
                or sum(courses[key].credits for key in minimum.course_ids)
                < minimum.required_credits
            ):
                raise RequirementSeedError(
                    "内訳条件の対象科目または必要単位が不正です。"
                )
        for group in policy.credit_groups:
            if not set(group.course_ids) <= associated:
                raise RequirementSeedError("修了規則の対象は本人課程の科目に限ります。")
            if (
                sum(courses[key].credits for key in group.course_ids)
                < group.required_credits
            ):
                raise RequirementSeedError(
                    "修了規則の対象単位が必要単位を満たしません。"
                )
            covered.update(group.course_ids)
        if (
            policy.degree_level == "master"
            and policy.catalog_status == "verified"
            and covered != associated
        ):
            raise RequirementSeedError(
                "大学院の単位区分が課程の全科目を含んでいません。"
            )
