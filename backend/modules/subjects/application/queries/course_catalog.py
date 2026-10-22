"""本人向け科目・分類の取得とトランザクションの契約。"""

from abc import ABC, abstractmethod

from modules.subjects.application.dto.course_catalog import CourseCatalog


class CourseCatalogRepository(ABC):
    @abstractmethod
    def get_catalog(self, curriculum_id: str) -> CourseCatalog: ...
