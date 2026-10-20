"""CreateCheckUseCaseの処理手順とトランザクション境界。"""

from uuid import uuid4

from modules.shared.grad_checker_shared.application.ports.clock import Clock

from ..dto.check_results import CheckInput, CheckRequest, SavedCheck
from ..errors.evaluation import EvaluationError
from ..ports.check_results import CheckUnitOfWork
from ..services.student_evaluation import evaluate_student


class CreateCheckUseCase:
    def __init__(self, uow: CheckUnitOfWork, clock: Clock) -> None:
        self.uow = uow
        self.clock = clock

    def execute(self, student_id: str, request: CheckRequest) -> SavedCheck:
        # 判定に使った成績版のまま保存するため、所属・成績・マスタの読取りから
        # 版の照合・判定・保存までを一つの書込みロックの下で行う。
        with self.uow.write():
            snapshot = self.uow.evaluation.get_snapshot(student_id)
            # 画面が最後に保存・取得した成績版で判定したことを保証する。
            if snapshot.data_revision != request.expected_revision:
                raise EvaluationError(
                    "revision_conflict", "成績・所属が別の画面で更新されました。"
                )
            snapshot = snapshot.model_copy(
                update={"completion_answers": request.completion_answers}
            )
            created_at = self.clock.now()
            grades = sorted(
                snapshot.grades, key=lambda grade: (grade.course_id, grade.attempt_no)
            )
            check = SavedCheck(
                id=uuid4(),
                created_at=created_at,
                input=CheckInput(
                    program_id=snapshot.program_id,
                    curriculum_id=snapshot.curriculum_id,
                    data_revision=snapshot.data_revision,
                    grades=grades,
                    completion_answers=request.completion_answers,
                ),
                result=evaluate_student(snapshot, created_at),
            )
            self.uow.checks.add(student_id, check)
        # commitが成功してから結果を返す。
        return check
