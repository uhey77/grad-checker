"""認証情報の取得・保存、パスワード処理、トランザクションの契約。"""

from abc import ABC, abstractmethod
from datetime import datetime

from modules.shared.grad_checker_shared.application.ports.unit_of_work import UnitOfWork

from ..dto.auth import Account, StoredSession


class AccountRepository(ABC):
    @abstractmethod
    def take_attempt(
        self, key: str, now: datetime, window: int, limit: int
    ) -> None: ...

    @abstractmethod
    def register(
        self, username: str, password_hash: str, recovery_hash: str, now: datetime
    ) -> Account: ...

    @abstractmethod
    def reset_credentials(
        self,
        username: str,
        recovery_hash: str,
        password_hash: str,
        new_recovery_hash: str,
        now: datetime,
    ) -> str | None:
        """復旧コードが一致した場合だけ更新し、アカウントIDを返す。"""

    @abstractmethod
    def revoke_sessions(self, student_id: str, now: datetime) -> None: ...

    @abstractmethod
    def credentials(self, username: str) -> tuple[Account, str] | None: ...

    @abstractmethod
    def save_session(
        self,
        account: Account,
        token_hash: str,
        csrf: str,
        expires: datetime,
        password_hash: str,
    ) -> bool:
        """照合したパスワードハッシュが現在も有効な場合だけ保存する。"""

    @abstractmethod
    def session(self, token_hash: str, now: datetime) -> StoredSession | None: ...

    @abstractmethod
    def revoke_session(self, token_hash: str, now: datetime) -> None: ...


class AccountUnitOfWork(UnitOfWork):
    @property
    @abstractmethod
    def accounts(self) -> AccountRepository: ...


class Passwords(ABC):
    @abstractmethod
    def hash(self, password: str) -> str: ...

    @abstractmethod
    def verify(self, password_hash: str | None, password: str) -> bool: ...
