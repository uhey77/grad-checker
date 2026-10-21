"""GetDashboardUseCaseの処理手順とトランザクション境界。"""

from modules.requirements.application.dto.student_evaluation import StudentDashboard
from modules.requirements.application.services.student_evaluation import (
    evaluate_student,
    read_snapshot,
)
from modules.requirements.application.uow.student_evaluation import EvaluationUnitOfWork
from shared.application.ports.clock import Clock


class GetDashboardUseCase:
    def __init__(self, uow: EvaluationUnitOfWork, clock: Clock) -> None:
        self.uow = uow
        self.clock = clock

    def execute(self, student_id: str) -> StudentDashboard:
        snapshot = read_snapshot(self.uow, student_id)
        result = evaluate_student(snapshot, self.clock.now())
        return StudentDashboard(
            **result.model_dump(
                include={
                    "degree_level",
                    "completion_conditions",
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
