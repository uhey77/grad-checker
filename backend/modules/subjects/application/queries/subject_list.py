"""開発用科目一覧・課程の取得とトランザクションの契約。"""

from abc import ABC, abstractmethod
from uuid import UUID

from modules.subjects.application.dto.subject_list import (
    SubjectList,
    SubjectListProgram,
)


class SubjectListRepository(ABC):
    @abstractmethod
    def list_programs(self) -> list[SubjectListProgram]:
        """選択できる課程一覧を取得する。"""

    @abstractmethod
    def get_subject_list(self, curriculum_id: UUID) -> SubjectList:
        """指定課程の科目一覧を取得する。"""
