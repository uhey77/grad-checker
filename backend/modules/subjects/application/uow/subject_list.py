from abc import abstractmethod

from modules.subjects.application.queries.subject_list import SubjectListRepository
from shared.application.uow.unit_of_work import UnitOfWork


class SubjectListUnitOfWork(UnitOfWork):
    @property
    @abstractmethod
    def subject_list(self) -> SubjectListRepository: ...
