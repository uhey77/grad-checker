"""EvaluateGraduationUseCaseの処理手順とトランザクション境界。"""

from modules.requirements.application.dto.student_evaluation import StudentEvaluation
from modules.requirements.application.services.student_evaluation import (
    evaluate_student,
    read_snapshot,
)
from modules.requirements.application.uow.student_evaluation import EvaluationUnitOfWork
from shared.application.ports.clock import Clock


class EvaluateGraduationUseCase:
    def __init__(self, uow: EvaluationUnitOfWork, clock: Clock) -> None:
        self.uow = uow
        self.clock = clock

    def execute(self, student_id: str) -> StudentEvaluation:
        return evaluate_student(read_snapshot(self.uow, student_id), self.clock.now())
