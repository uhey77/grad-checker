"""本人の保存済みデータを取得し、最新の卒業単位条件を計算する。"""

from datetime import UTC, datetime
from typing import Protocol

from .evaluation import evaluate_graduation
from .evaluation_models import EvaluationResult, EvaluationSnapshot


class EvaluationRepository(Protocol):
    def get_snapshot(self, student_id: str) -> EvaluationSnapshot: ...


class StudentEvaluation(EvaluationResult):
    evaluated_at: datetime


def evaluate_student(
    snapshot: EvaluationSnapshot, evaluated_at: datetime
) -> StudentEvaluation:
    result = evaluate_graduation(snapshot)
    return StudentEvaluation(**result.model_dump(), evaluated_at=evaluated_at)


class EvaluationService:
    def __init__(self, repository: EvaluationRepository) -> None:
        self.repository = repository

    def evaluate(self, student_id: str) -> StudentEvaluation:
        snapshot = self.repository.get_snapshot(student_id)
        return evaluate_student(snapshot, datetime.now(UTC))
