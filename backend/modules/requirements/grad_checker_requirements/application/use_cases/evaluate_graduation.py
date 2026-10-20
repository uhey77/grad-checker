"""EvaluateGraduationUseCaseの処理手順とトランザクション境界。"""

from modules.shared.grad_checker_shared.application.ports.clock import Clock

from ..dto.student_evaluation import StudentEvaluation
from ..ports.student_evaluation import EvaluationUnitOfWork
from ..services.student_evaluation import evaluate_student, read_snapshot


class EvaluateGraduationUseCase:
    def __init__(self, uow: EvaluationUnitOfWork, clock: Clock) -> None:
        self.uow = uow
        self.clock = clock

    def execute(self, student_id: str) -> StudentEvaluation:
        return evaluate_student(read_snapshot(self.uow, student_id), self.clock.now())
