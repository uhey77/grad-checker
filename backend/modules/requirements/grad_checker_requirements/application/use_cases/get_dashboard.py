"""GetDashboardUseCaseの処理手順とトランザクション境界。"""

from modules.shared.grad_checker_shared.application.clock import Clock

from ..student_evaluation import (
    EvaluationUnitOfWork,
    StudentDashboard,
    evaluate_student,
    read_snapshot,
)


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
