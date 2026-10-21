"""このモジュールのRepository・Queryを束ねるSQLiteのUnit of Work実装。"""

from sqlalchemy import Engine

from modules.accounts.application.uow.auth import AccountUnitOfWork
from modules.accounts.application.uow.profile import ProfileUnitOfWork
from modules.accounts.infrastructure.persistence.repositories.profile import (
    SqliteProfileRepository,
)
from modules.accounts.infrastructure.persistence.repositories.profile import (
    unavailable as profile_unavailable,
)
from modules.accounts.infrastructure.persistence.repositories.repository import (
    SqliteAccountRepository,
    auth_failure,
)
from shared.infrastructure.persistence.unit_of_work import SqlUnitOfWork


class SqliteProfileUnitOfWork(SqlUnitOfWork, ProfileUnitOfWork):
    def __init__(self, engine: Engine) -> None:
        super().__init__(engine, profile_unavailable)

    @property
    def profiles(self) -> SqliteProfileRepository:
        return SqliteProfileRepository(self.session)


class SqliteAccountUnitOfWork(SqlUnitOfWork, AccountUnitOfWork):
    def __init__(self, engine: Engine) -> None:
        super().__init__(engine, auth_failure)

    @property
    def accounts(self) -> SqliteAccountRepository:
        return SqliteAccountRepository(self.session)
