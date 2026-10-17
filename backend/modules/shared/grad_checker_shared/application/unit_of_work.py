"""ユースケースが決めるトランザクション境界の契約。"""

from abc import ABC, abstractmethod
from contextlib import AbstractContextManager


class UnitOfWork(ABC):
    """一つの業務操作で使うリポジトリを、同じトランザクションに束ねる。

    各モジュールはこれを継承し、使用するリポジトリを抽象プロパティで宣言する。
    リポジトリは ``read`` ・ ``write`` のブロック内でだけ使用できる。
    """

    @abstractmethod
    def read(self) -> AbstractContextManager[None]:
        """複数の読取りを一つのスナップショットで行い、終了時に何も保存しない。"""

    @abstractmethod
    def write(self) -> AbstractContextManager[None]:
        """正常終了でcommitし、例外が発生した場合は全体をロールバックする。"""
