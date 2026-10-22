"""科目マスタの追加投入とトランザクションの契約。"""

from abc import ABC, abstractmethod

from modules.subjects.application.dto.subject_data import SubjectDataSeed


class SubjectDataStore(ABC):
    @abstractmethod
    def load(self) -> SubjectDataSeed:
        """投入済みの課程・科目データをすべて読む。"""

    @abstractmethod
    def insert(self, additions: SubjectDataSeed) -> None:
        """テーブルの順、各テーブル内では並びの順に追加する。"""
