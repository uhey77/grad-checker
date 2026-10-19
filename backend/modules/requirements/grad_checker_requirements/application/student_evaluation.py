"""本人の保存済みデータを取得し、最新の卒業単位条件を計算する。"""

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel

from modules.shared.grad_checker_shared.application.unit_of_work import UnitOfWork

from .evaluation import evaluate_graduation
from .evaluation_models import (
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


class EvaluationService:
    def __init__(self, uow: EvaluationUnitOfWork) -> None:
        self.uow = uow

    def evaluate(self, student_id: str) -> StudentEvaluation:
        return evaluate_student(self._snapshot(student_id), datetime.now(UTC))

    def dashboard(self, student_id: str) -> StudentDashboard:
        snapshot = self._snapshot(student_id)
        result = evaluate_student(snapshot, datetime.now(UTC))
        return StudentDashboard(
            **result.model_dump(
                include={
                    "result",
                    "evaluated_at",
                    "data_revision",
                    "curriculum",
                    "rule_revisions",
                    "total",
                    "categories",
                    "warnings",
                }
            ),
            curriculum_revision=result.curriculum.revision,
            grade_count=len(snapshot.grades),
        )

    def _snapshot(self, student_id: str) -> EvaluationSnapshot:
        # 読取り専用。履歴作成や成績版の更新は行わない。
        with self.uow.read():
            snapshot = self.uow.evaluation.get_snapshot(student_id)
        # 判定の計算はスナップショットの取得後、トランザクションの外で行う。
        return snapshot
