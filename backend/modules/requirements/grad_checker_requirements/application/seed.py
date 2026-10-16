"""要件・規則シードの入力契約。既存の科目マスタとは別に追加投入する。"""

from typing import Self
from uuid import UUID

from pydantic import model_validator

from modules.requirements.grad_checker_requirements.domain.requirement import (
    CreditRuleKind,
    RequirementKind,
)
from modules.subjects.grad_checker_subjects.application.subject_data_validation import (
    NonemptyText,
    NonnegativeInteger,
    PositiveInteger,
    SeedRecord,
)
from modules.subjects.grad_checker_subjects.domain import curriculum_verification_status

VerificationStatus = curriculum_verification_status.VerificationStatus


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

    @model_validator(mode="after")
    def verification_matches_reason(self) -> Self:
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
