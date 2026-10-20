"""ユースケースのトランザクション範囲を検証するFakeのUnit of Work。"""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime

from modules.shared.grad_checker_shared.application.ports.clock import Clock
from modules.shared.grad_checker_shared.application.ports.unit_of_work import UnitOfWork


class FakeUnitOfWork(UnitOfWork):
    """開始したブロックとcommit・ロールバックを ``events`` に記録する。

    メモリ上のリポジトリは ``require_block`` で、ブロック外の使用を拒否する。
    """

    def __init__(self) -> None:
        self.events: list[str] = []
        self._active = False

    @contextmanager
    def read(self) -> Generator[None]:
        with self._block("read"):
            yield

    @contextmanager
    def write(self) -> Generator[None]:
        with self._block("write"):
            try:
                yield
            except BaseException:
                self.events.append("rollback")
                raise
            self.events.append("commit")

    @property
    def active(self) -> bool:
        return self._active

    def require_block(self) -> None:
        if not self._active:
            raise RuntimeError("リポジトリはread・writeのブロック内で使用する。")

    @contextmanager
    def _block(self, kind: str) -> Generator[None]:
        if self._active:
            raise RuntimeError("トランザクションは入れ子にできません。")
        self.events.append(kind)
        self._active = True
        try:
            yield
        finally:
            self._active = False


class FixedClock(Clock):
    def __init__(self, value: datetime | None = None) -> None:
        self.value = value or datetime(2026, 10, 20, tzinfo=UTC)

    def now(self) -> datetime:
        return self.value
