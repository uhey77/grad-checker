"""本人向け科目・分類の取得とトランザクションの契約。"""

from abc import ABC, abstractmethod

from modules.shared.grad_checker_shared.application.ports.unit_of_work import UnitOfWork

from ..dto.course_catalog import CourseCatalog


class CourseCatalogRepository(ABC):
    @abstractmethod
    def get_catalog(self, curriculum_id: str) -> CourseCatalog: ...


class CourseCatalogUnitOfWork(UnitOfWork):
    @property
    @abstractmethod
    def catalog(self) -> CourseCatalogRepository: ...
