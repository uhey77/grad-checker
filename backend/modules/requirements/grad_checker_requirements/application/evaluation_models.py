"""DB・HTTPから独立した卒業単位判定の入出力契約。"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from modules.grades.grad_checker_grades.application.grades import GradeAttempt
from modules.requirements.grad_checker_requirements.application.seed import (
    RequirementSeed,
)
from modules.requirements.grad_checker_requirements.domain.requirement import (
    RequirementKind,
)
from modules.subjects.grad_checker_subjects.application.subject_data_validation import (
    CurriculumData,
    NonnegativeInteger,
    SubjectDataSeed,
)

type Judgment = Literal["pass", "fail"]
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


class CreditSummary(BaseModel):
    required_credits: int
    earned_credits: int
    credited_credits: int
    shortage: int
    result: Judgment


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


class ExternalAllocation(BaseModel):
    rule_id: UUID
    target_classification_id: UUID
    target_name: str
    earned_credits: int
    credited_credits: int
    free_credits: int


class EvaluationResult(BaseModel):
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
