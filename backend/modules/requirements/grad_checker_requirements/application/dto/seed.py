"""卒業要件・算入規則の投入用モデル。"""

from typing import Literal, Self
from uuid import UUID

from pydantic import Field, model_validator

from modules.subjects.grad_checker_subjects.public import (
    NonemptyText,
    NonnegativeInteger,
    PositiveInteger,
    SeedRecord,
    VerificationStatus,
)

from ...domain.requirement import CreditRuleKind, RequirementKind
from .completion_policy import CompletionPolicyData


class RequirementData(SeedRecord):
    id: UUID
    curriculum_id: UUID
    code: NonemptyText
    name: NonemptyText
    kind: RequirementKind
    required_credits: NonnegativeInteger
    classification_id: UUID | None = None
    parent_id: UUID | None = None
    display_order: NonnegativeInteger = 0
    source_document: NonemptyText
    source_pages: NonemptyText


class RequirementScopeData(SeedRecord):
    id: UUID
    curriculum_id: UUID
    requirement_id: UUID
    classification_id: UUID | None = None
    course_id: UUID | None = None

    @model_validator(mode="after")
    def exactly_one_target(self) -> Self:
        if (self.classification_id is None) == (self.course_id is None):
            raise ValueError("分類または科目の片方だけを指定してください。")
        return self


class CreditRuleData(SeedRecord):
    id: UUID
    curriculum_id: UUID
    code: NonemptyText
    kind: CreditRuleKind
    verification_status: VerificationStatus
    source_document: NonemptyText
    source_pages: NonemptyText
    source_note: NonemptyText
    unresolved_reason: NonemptyText | None = None
    revision: PositiveInteger
    allocation_policy: Literal["chronological_best_fit_v1"] | None = None

    @model_validator(mode="after")
    def verification_matches_reason(self) -> Self:
        if (
            self.allocation_policy is not None
            and self.kind != CreditRuleKind.OTHER_FACULTY
        ):
            raise ValueError("取得順の配分方針は他学部算入にだけ指定できます。")
        if (self.verification_status == VerificationStatus.UNVERIFIED) != (
            self.unresolved_reason is not None
        ):
            raise ValueError(
                "未確認規則には未確認理由が必要です。確認済みには指定できません。"
            )
        return self


class CreditRuleCourseData(SeedRecord):
    curriculum_id: UUID
    rule_id: UUID
    course_id: UUID
    target_classification_id: UUID


class CreditRuleLimitData(SeedRecord):
    id: UUID
    rule_id: UUID
    limit_group_code: NonemptyText
    max_credits: NonnegativeInteger


class RequirementSeed(SeedRecord):
    graduation_requirements: list[RequirementData]
    requirement_scopes: list[RequirementScopeData]
    credit_rules: list[CreditRuleData]
    credit_rule_courses: list[CreditRuleCourseData]
    credit_rule_limits: list[CreditRuleLimitData]
    completion_policies: list[CompletionPolicyData] = Field(default_factory=list)
