from abc import abstractmethod

from modules.subjects.application.queries.course_catalog import CourseCatalogRepository
from shared.application.uow.unit_of_work import UnitOfWork


class CourseCatalogUnitOfWork(UnitOfWork):
    @property
    @abstractmethod
    def catalog(self) -> CourseCatalogRepository: ...
