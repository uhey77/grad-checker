"""科目マスタの追加投入とトランザクションの契約。"""

from abc import ABC, abstractmethod

from modules.shared.grad_checker_shared.application.ports.unit_of_work import UnitOfWork

from ..dto.subject_data import SubjectDataSeed


class SubjectDataStore(ABC):
    @abstractmethod
    def load(self) -> SubjectDataSeed:
        """投入済みの課程・科目データをすべて読む。"""

    @abstractmethod
    def insert(self, additions: SubjectDataSeed) -> None:
        """テーブルの順、各テーブル内では並びの順に追加する。"""


class SubjectDataUnitOfWork(UnitOfWork):
    @property
    @abstractmethod
    def subject_data(self) -> SubjectDataStore: ...
