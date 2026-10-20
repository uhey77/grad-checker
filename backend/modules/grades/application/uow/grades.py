from abc import abstractmethod

from modules.grades.application.ports.grades import GradeRepository
from shared.application.uow.unit_of_work import UnitOfWork


class GradeUnitOfWork(UnitOfWork):
    @property
    @abstractmethod
    def grades(self) -> GradeRepository: ...
