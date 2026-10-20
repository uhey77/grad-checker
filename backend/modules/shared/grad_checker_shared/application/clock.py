"""業務処理が利用する現在時刻の契約。"""

from abc import ABC, abstractmethod
from datetime import datetime


class Clock(ABC):
    @abstractmethod
    def now(self) -> datetime:
        """タイムゾーン付きのUTC日時を返す。"""
