"""本人の判定用スナップショット取得とトランザクションの契約。"""

from abc import ABC, abstractmethod

from modules.requirements.application.dto.evaluation import EvaluationSnapshot


class EvaluationRepository(ABC):
    @abstractmethod
    def get_snapshot(self, student_id: str) -> EvaluationSnapshot:
        """所属・成績・マスタを、呼出し側が開始したトランザクション内で読む。"""
