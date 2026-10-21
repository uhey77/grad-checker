from abc import abstractmethod

from modules.accounts.application.ports.profile import ProfileRepository
from shared.application.uow.unit_of_work import UnitOfWork


class ProfileUnitOfWork(UnitOfWork):
    @property
    @abstractmethod
    def profiles(self) -> ProfileRepository: ...
