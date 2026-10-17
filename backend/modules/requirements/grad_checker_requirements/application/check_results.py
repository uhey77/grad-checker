"""本人が実行した卒業要件チェックを、当時の入力・結果とともに履歴として保存する。"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from modules.grades.grad_checker_grades.application.grades import GradeAttempt

from .errors.evaluation import EvaluationError
from .evaluation_models import EvaluationSnapshot
from .student_evaluation import StudentEvaluation, evaluate_student

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


type BuildCheck = Callable[[EvaluationSnapshot], SavedCheck]


class CheckRepository(Protocol):
    def create_check(self, student_id: str, build: BuildCheck) -> SavedCheck:
        """同じ書込みトランザクションで読んだスナップショットから履歴を作り保存する。"""
        ...

    def get_check(self, student_id: str, check_id: UUID) -> SavedCheck | None: ...


class CheckService:
    def __init__(self, repository: CheckRepository) -> None:
        self.repository = repository

    def create_check(self, student_id: str, request: CheckRequest) -> SavedCheck:
        def build(snapshot: EvaluationSnapshot) -> SavedCheck:
            # 画面が最後に保存・取得した成績版で判定したことを保証する。
            if snapshot.data_revision != request.expected_revision:
                raise EvaluationError(
                    "revision_conflict", "成績・所属が別の画面で更新されました。"
                )
            created_at = datetime.now(UTC)
            grades = sorted(
                snapshot.grades, key=lambda grade: (grade.course_id, grade.attempt_no)
            )
            return SavedCheck(
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

        return self.repository.create_check(student_id, build)

    def get_check(self, student_id: str, check_id: UUID) -> SavedCheck:
        # 他人の履歴と存在しない履歴を区別しない。
        check = self.repository.get_check(student_id, check_id)
        if check is None:
            raise EvaluationError("check_not_found", "判定履歴が見つかりません。")
        return check
