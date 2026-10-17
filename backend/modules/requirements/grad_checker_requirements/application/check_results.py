"""本人が実行した卒業要件チェックを、当時の入力・結果とともに履歴として保存する。"""

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from modules.grades.grad_checker_grades.application.grades import GradeAttempt
from modules.shared.grad_checker_shared.application.unit_of_work import UnitOfWork

from .errors.evaluation import EvaluationError
from .student_evaluation import (
    EvaluationRepository,
    StudentEvaluation,
    evaluate_student,
)

MAX_REVISION = 9007199254740990


class CheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    expected_revision: int = Field(ge=0, le=MAX_REVISION)


class CheckInput(BaseModel):
    """判定に使った本人の課程・適用カリキュラム・全成績と成績版。"""

    program_id: UUID
    curriculum_id: UUID
    data_revision: int
    grades: list[GradeAttempt]


class SavedCheck(BaseModel):
    """保存済みの判定履歴。作成後は変更せず、現在のマスタで再計算しない。"""

    id: UUID
    created_at: datetime
    input: CheckInput
    result: StudentEvaluation


class CheckRepository(Protocol):
    def add(self, student_id: str, check: SavedCheck) -> None: ...
    def get(self, student_id: str, check_id: UUID) -> SavedCheck | None: ...


class CheckUnitOfWork(UnitOfWork, Protocol):
    @property
    def evaluation(self) -> EvaluationRepository: ...

    @property
    def checks(self) -> CheckRepository: ...


class CheckService:
    def __init__(self, uow: CheckUnitOfWork) -> None:
        self.uow = uow

    def create_check(self, student_id: str, request: CheckRequest) -> SavedCheck:
        # 判定に使った成績版のまま保存するため、所属・成績・マスタの読取りから
        # 版の照合・判定・保存までを一つの書込みロックの下で行う。
        with self.uow.write():
            snapshot = self.uow.evaluation.get_snapshot(student_id)
            # 画面が最後に保存・取得した成績版で判定したことを保証する。
            if snapshot.data_revision != request.expected_revision:
                raise EvaluationError(
                    "revision_conflict", "成績・所属が別の画面で更新されました。"
                )
            created_at = datetime.now(UTC)
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
                ),
                result=evaluate_student(snapshot, created_at),
            )
            self.uow.checks.add(student_id, check)
        # commitが成功してから結果を返す。
        return check

    def get_check(self, student_id: str, check_id: UUID) -> SavedCheck:
        with self.uow.read():
            check = self.uow.checks.get(student_id, check_id)
        # 他人の履歴と存在しない履歴を区別しない。
        if check is None:
            raise EvaluationError("check_not_found", "判定履歴が見つかりません。")
        return check
