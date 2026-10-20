"""本人が実行した卒業要件チェックを、当時の入力・結果とともに履歴として保存する。"""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from modules.grades.grad_checker_grades.public import GradeAttempt
from modules.shared.grad_checker_shared.application.unit_of_work import UnitOfWork

from .completion_policy import CompletionAnswer
from .evaluation_models import CreditSummary, Judgment
from .student_evaluation import (
    EvaluationRepository,
    StudentEvaluation,
)

MAX_REVISION = 9007199254740990
MAX_CHECK_PAGE_SIZE = 100


class CheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    expected_revision: int = Field(ge=0, le=MAX_REVISION)
    completion_answers: list[CompletionAnswer] = Field(
        default_factory=list, max_length=50
    )


class CheckInput(BaseModel):
    """判定に使った本人の課程・適用カリキュラム・全成績と成績版。"""

    program_id: UUID
    curriculum_id: UUID
    data_revision: int
    grades: list[GradeAttempt]
    completion_answers: list[CompletionAnswer] = Field(default_factory=list)


class SavedCheck(BaseModel):
    """保存済みの判定履歴。作成後は変更せず、現在のマスタで再計算しない。"""

    id: UUID
    created_at: datetime
    input: CheckInput
    result: StudentEvaluation


class CheckPage(BaseModel):
    """履歴一覧の取得範囲。作成日時の降順・同時刻はID順に数える。"""

    model_config = ConfigDict(extra="forbid", strict=True)
    limit: int = Field(ge=1, le=MAX_CHECK_PAGE_SIZE)
    offset: int = Field(ge=0, le=MAX_REVISION)


class CheckCurriculum(BaseModel):
    """判定当時の課程名と規則版。保存済みの結果から読む。"""

    id: UUID
    code: str
    name: str
    revision: int


class CheckSummary(BaseModel):
    """一覧に表示する保存済み判定の要約。現在のマスタで再計算しない。"""

    id: UUID
    created_at: datetime
    data_revision: int
    result: Judgment
    curriculum: CheckCurriculum
    total: CreditSummary


class CheckList(BaseModel):
    checks: list[CheckSummary]
    limit: int
    offset: int
    total_count: int


class CheckRepository(ABC):
    @abstractmethod
    def add(self, student_id: str, check: SavedCheck) -> None: ...

    @abstractmethod
    def get(self, student_id: str, check_id: UUID) -> SavedCheck | None: ...

    @abstractmethod
    def count(self, student_id: str) -> int: ...

    @abstractmethod
    def list_page(self, student_id: str, page: CheckPage) -> list[CheckSummary]:
        """本人の履歴を作成日時の降順・同時刻はID順で返す。"""


class CheckUnitOfWork(UnitOfWork):
    @property
    @abstractmethod
    def evaluation(self) -> EvaluationRepository: ...

    @property
    @abstractmethod
    def checks(self) -> CheckRepository: ...
