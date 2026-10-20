"""本人の判定履歴の保存・取得とトランザクションの契約。"""

from abc import ABC, abstractmethod
from uuid import UUID

from modules.shared.grad_checker_shared.application.ports.unit_of_work import UnitOfWork

from ..dto.check_results import CheckPage, CheckSummary, SavedCheck
from .student_evaluation import EvaluationRepository


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
