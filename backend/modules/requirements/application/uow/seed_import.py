from abc import abstractmethod

from modules.requirements.application.ports.seed_import import RequirementDataStore
from shared.application.uow.unit_of_work import UnitOfWork


class RequirementUnitOfWork(UnitOfWork):
    @property
    @abstractmethod
    def requirements(self) -> RequirementDataStore: ...
