"""リポジトリで共通のトランザクション境界と、DB例外の業務エラーへの変換。"""

from collections.abc import Callable, Generator
from contextlib import contextmanager

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from modules.shared.grad_checker_shared.application.errors import BusinessError

type TranslateError = Callable[[SQLAlchemyError], BusinessError]


@contextmanager
def database_errors(translate: TranslateError) -> Generator[None]:
    """DBライブラリの例外を、呼出し側モジュールの業務エラーへ変換する。"""
    try:
        yield
    except SQLAlchemyError as error:
        raise translate(error) from error


@contextmanager
def read_snapshot(session: Session, translate: TranslateError) -> Generator[None]:
    """複数SELECTを一つの読取スナップショットで行う。"""
    with database_errors(translate):
        # SQLiteの従来トランザクションモードでも複数SELECTの一貫性を保証する。
        session.connection().exec_driver_sql("BEGIN")
        yield


@contextmanager
def write_transaction(
    session: Session, translate: TranslateError, *, immediate: bool = True
) -> Generator[None]:
    """一連の書込みをcommitし、途中で失敗した場合は全体をロールバックする。"""
    try:
        if immediate:
            # 最初に書込みロックを取得し、確認から更新までを直列化する。
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        yield
        session.commit()
    except SQLAlchemyError as error:
        session.rollback()
        raise translate(error) from error
    except BaseException:
        session.rollback()
        raise
