"""本人向けの卒業判定とダッシュボードの出力。"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from modules.requirements.application.dto.evaluation import (
    CompletionConditionResult,
    ConditionResult,
    CreditSummary,
    EvaluationResult,
    EvaluationWarning,
    Judgment,
)
from modules.subjects.public import CurriculumData


class StudentEvaluation(EvaluationResult):
    evaluated_at: datetime
    # 判定条件を増やさず、既存の必修条件を科目区分別に表示するための内訳。
    required_course_breakdowns: list[ConditionResult] = Field(default_factory=list)


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
