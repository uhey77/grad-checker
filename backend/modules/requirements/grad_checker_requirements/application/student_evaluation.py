"""本人の保存済みデータを取得し、最新の卒業単位条件を計算する。"""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from modules.shared.grad_checker_shared.application.unit_of_work import UnitOfWork

from .evaluation import evaluate_graduation
from .evaluation_models import (
    CompletionConditionResult,
    ConditionResult,
    CreditSummary,
    CurriculumData,
    EvaluationResult,
    EvaluationSnapshot,
    EvaluationWarning,
    Judgment,
)


class EvaluationRepository(ABC):
    @abstractmethod
    def get_snapshot(self, student_id: str) -> EvaluationSnapshot:
        """所属・成績・マスタを、呼出し側が開始したトランザクション内で読む。"""


class EvaluationUnitOfWork(UnitOfWork):
    @property
    @abstractmethod
    def evaluation(self) -> EvaluationRepository: ...


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


def evaluate_student(
    snapshot: EvaluationSnapshot, evaluated_at: datetime
) -> StudentEvaluation:
    result = evaluate_graduation(snapshot)
    return StudentEvaluation(**result.model_dump(), evaluated_at=evaluated_at)


def read_snapshot(uow: EvaluationUnitOfWork, student_id: str) -> EvaluationSnapshot:
    # 判定の計算は読取りトランザクションを閉じた後に行う。
    with uow.read():
        return uow.evaluation.get_snapshot(student_id)
