"""実行環境の時計をUTCで取得する。"""

from datetime import UTC, datetime

from ..application.clock import Clock


class SystemClock(Clock):
    def now(self) -> datetime:
        return datetime.now(UTC)
