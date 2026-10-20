"""判定用スナップショットの取得と日時を含む判定結果の組立て。"""

from datetime import datetime

from ..dto.evaluation import EvaluationSnapshot
from ..dto.student_evaluation import StudentEvaluation
from ..ports.student_evaluation import EvaluationUnitOfWork
from .evaluation import evaluate_graduation


def evaluate_student(
    snapshot: EvaluationSnapshot, evaluated_at: datetime
) -> StudentEvaluation:
    result = evaluate_graduation(snapshot)
    return StudentEvaluation(**result.model_dump(), evaluated_at=evaluated_at)


def read_snapshot(uow: EvaluationUnitOfWork, student_id: str) -> EvaluationSnapshot:
    # 判定の計算は読取りトランザクションを閉じた後に行う。
    with uow.read():
        return uow.evaluation.get_snapshot(student_id)
