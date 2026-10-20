from abc import abstractmethod

from modules.accounts.application.ports.auth import AccountRepository
from shared.application.uow.unit_of_work import UnitOfWork


class AccountUnitOfWork(UnitOfWork):
    @property
    @abstractmethod
    def accounts(self) -> AccountRepository: ...
