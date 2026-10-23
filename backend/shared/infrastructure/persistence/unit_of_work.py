"""DBごとのトランザクションでUnit of Workを実装する共通基底。"""

from collections.abc import Callable, Generator
from contextlib import contextmanager

from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from shared.application.errors.business import BusinessError
from shared.application.uow.unit_of_work import UnitOfWork

type TranslateError = Callable[[SQLAlchemyError], BusinessError]

# SQLiteのBEGIN IMMEDIATEと同じ書込み直列化を維持する。全プロセスで共通。
WRITE_LOCK_KEY = 0x6772616463686563


def lock_postgres_writes(connection: Connection) -> None:
    connection.execute(
        text("SELECT pg_advisory_xact_lock(:key)"), {"key": WRITE_LOCK_KEY}
    )


class SqlUnitOfWork(UnitOfWork):
    """``read`` ・ ``write`` のブロックごとにSessionを開き、終了時に閉じる。

    各モジュールはこれと自モジュールのUnit of Work契約を継承し、``session`` から
    リポジトリを生成するプロパティを定義する。DB例外を自モジュールの業務エラーへ
    変換する関数を渡す。
    """

    def __init__(self, engine: Engine, translate: TranslateError) -> None:
        self._engine = engine
        self._translate = translate
        self._session: Session | None = None

    @property
    def session(self) -> Session:
        if self._session is None:
            raise RuntimeError("リポジトリはread・writeのブロック内で使用する。")
        return self._session

    @contextmanager
    def read(self) -> Generator[None]:
        with self._open() as session:
            try:
                # SQLiteの従来トランザクションモードでも複数SELECTの一貫性を保証する。
                if self._engine.dialect.name == "sqlite":
                    session.connection().exec_driver_sql("BEGIN")
                else:
                    session.connection(
                        execution_options={"isolation_level": "REPEATABLE READ"}
                    )
                yield
            except SQLAlchemyError as error:
                raise self._translate(error) from error
            finally:
                # 読取りでは変更を残さない。
                session.rollback()

    @contextmanager
    def write(self) -> Generator[None]:
        with self._open() as session:
            try:
                # 最初に書込みロックを取得し、確認から更新までを直列化する。
                if self._engine.dialect.name == "sqlite":
                    session.connection().exec_driver_sql("BEGIN IMMEDIATE")
                else:
                    # READ COMMITTEDでロック待機後の最新状態を読む。
                    lock_postgres_writes(session.connection())
                yield
                session.commit()
            except SQLAlchemyError as error:
                session.rollback()
                raise self._translate(error) from error
            except BaseException:
                session.rollback()
                raise

    @contextmanager
    def _open(self) -> Generator[Session]:
        if self._session is not None:
            raise RuntimeError("トランザクションは入れ子にできません。")
        with Session(self._engine) as session:
            self._session = session
            try:
                yield session
            finally:
                self._session = None
