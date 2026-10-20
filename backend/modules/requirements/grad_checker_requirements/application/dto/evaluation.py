"""卒業判定に必要なスナップショットと判定結果の入出力。"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from modules.grades.grad_checker_grades.public import GradeAttempt
from modules.subjects.grad_checker_subjects.public import (
    CurriculumData,
    NonnegativeInteger,
    SubjectDataSeed,
    SubjectOfferingData,
)

from ...domain.requirement import RequirementKind
from .completion_policy import CompletionAnswer, NonCreditCondition
from .seed import RequirementSeed

type Judgment = Literal["pass", "fail", "pending"]


type EvaluationWarning = Literal["provisional_external_allocation"]


class EvaluationSnapshot(BaseModel):
    """呼出し側が同じ読取時点で取得する所属・成績・マスタ。

    マスタのPydantic契約は投入処理と共有する。ファイルやDBモデルは受け取らない。
    """

    model_config = ConfigDict(extra="forbid")
    program_id: UUID
    curriculum_id: UUID
    data_revision: NonnegativeInteger
    grades: list[GradeAttempt]
    subjects: SubjectDataSeed
    requirements: RequirementSeed
    completion_answers: list[CompletionAnswer] = Field(default_factory=list)


class CreditSummary(BaseModel):
    required_credits: int
    earned_credits: int
    credited_credits: int
    shortage: int
    result: Literal["pass", "fail"]


class ConditionResult(CreditSummary):
    id: UUID
    code: str
    name: str
    kind: RequirementKind
    parent_id: UUID | None
    classification_id: UUID | None


class CourseResult(BaseModel):
    course_id: UUID
    name: str
    classification_id: UUID | None
    credits: int
    status: Literal["earned", "not_earned", "pending", "not_taken"]
    latest_attempt: GradeAttempt | None


class OverflowAllocation(BaseModel):
    rule_id: UUID
    requirement_id: UUID
    target_classification_id: UUID
    earned_credits: int
    group_credits: int
    overflow_credits: int
    transferred_credits: int


class RecommendationReason(BaseModel):
    requirement_id: UUID
    code: str
    name: str
    shortage_reduction: int
    reason: str


class CourseRecommendation(CourseResult):
    is_required: bool
    offerings: list[SubjectOfferingData]
    contributions: list[RecommendationReason]


class ExternalAllocation(BaseModel):
    rule_id: UUID
    target_classification_id: UUID
    target_name: str
    earned_credits: int
    credited_credits: int
    free_credits: int


class CompletionConditionResult(NonCreditCondition):
    status: Literal["met", "not_met", "unknown"]


class EvaluationResult(BaseModel):
    degree_level: Literal["bachelor", "master", "doctoral"] = "bachelor"
    completion_conditions: list[CompletionConditionResult] = Field(default_factory=list)
    result: Judgment
    data_revision: int
    curriculum: CurriculumData
    rule_revisions: dict[UUID, int]
    total: CreditSummary
    categories: list[ConditionResult]
    requirements: list[ConditionResult]
    courses: list[CourseResult]
    missing_required_courses: list[CourseResult]
    allocations: list[OverflowAllocation]
    external_allocations: list[ExternalAllocation]
    warnings: list[EvaluationWarning]
    # 推薦導入前の保存済み履歴には情報がない。現在のマスタで補完しない。
    recommendations: list[CourseRecommendation] | None = None
