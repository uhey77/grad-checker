"""本人向けの卒業判定とダッシュボードの出力。"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from modules.subjects.grad_checker_subjects.public import CurriculumData

from .evaluation import (
    CompletionConditionResult,
    ConditionResult,
    CreditSummary,
    EvaluationResult,
    EvaluationWarning,
    Judgment,
)


class StudentEvaluation(EvaluationResult):
    evaluated_at: datetime


class StudentDashboard(BaseModel):
    degree_level: str = "bachelor"
    completion_conditions: list[CompletionConditionResult] = Field(default_factory=list)
    result: Judgment
    evaluated_at: datetime
    data_revision: int
    curriculum_revision: int
    curriculum: CurriculumData
    rule_revisions: dict[UUID, int]
    grade_count: int
    total: CreditSummary
    categories: list[ConditionResult]
    warnings: list[EvaluationWarning]
