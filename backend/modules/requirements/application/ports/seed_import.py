"""卒業要件マスタの追加投入とトランザクションの契約。"""

from abc import ABC, abstractmethod

from modules.requirements.application.dto.seed import RequirementSeed
from modules.subjects.public import SubjectDataSeed


class RequirementDataStore(ABC):
    @abstractmethod
    def subjects(self) -> SubjectDataSeed:
        """要件が参照する、投入済みの課程・科目データを読む。"""

    @abstractmethod
    def load(self) -> RequirementSeed:
        """投入済みの要件マスタをすべて読む。"""

    @abstractmethod
    def insert(self, additions: RequirementSeed) -> None:
        """テーブルの順、各テーブル内では並びの順に追加する。"""
