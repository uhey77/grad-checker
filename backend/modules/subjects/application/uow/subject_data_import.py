from abc import abstractmethod

from modules.subjects.application.ports.subject_data_import import SubjectDataStore
from shared.application.uow.unit_of_work import UnitOfWork


class SubjectDataUnitOfWork(UnitOfWork):
    @property
    @abstractmethod
    def subject_data(self) -> SubjectDataStore: ...
