"""共通Unit of Workのcommit・ロールバック・DB例外の変換を一時SQLiteで検証する。"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from shared.application.errors.business import BusinessError
from shared.infrastructure.persistence.database import create_database_engine
from shared.infrastructure.persistence.unit_of_work import SqlUnitOfWork


class UnavailableError(BusinessError):
    code = "unavailable"


class RejectedError(BusinessError):
    code = "rejected"


@pytest.fixture
def engine(tmp_path: Path) -> Iterator[Engine]:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'uow.db'}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE items (id INTEGER PRIMARY KEY)"))
    yield engine
    engine.dispose()


def unit_of_work(engine: Engine) -> SqlUnitOfWork:
    return SqlUnitOfWork(engine, lambda _error: UnavailableError())


def insert(uow: SqlUnitOfWork, item_id: int) -> None:
    uow.session.connection().execute(
        text("INSERT INTO items (id) VALUES (:id)"), {"id": item_id}
    )


def items(engine: Engine) -> list[int]:
    with engine.connect() as connection:
        return list(connection.execute(text("SELECT id FROM items")).scalars())


def test_write_commits_all_changes_on_success(engine) -> None:
    uow = unit_of_work(engine)
    with uow.write():
        insert(uow, 1)
        insert(uow, 2)
    assert items(engine) == [1, 2]


def test_write_rolls_back_all_changes_on_business_error(engine) -> None:
    uow = unit_of_work(engine)
    with pytest.raises(RejectedError), uow.write():
        insert(uow, 1)
        raise RejectedError
    assert items(engine) == []


def test_write_translates_database_errors_and_rolls_back(engine) -> None:
    uow = unit_of_work(engine)
    with pytest.raises(UnavailableError), uow.write():
        insert(uow, 1)
        insert(uow, 1)
    assert items(engine) == []


def test_read_never_keeps_changes(engine) -> None:
    uow = unit_of_work(engine)
    with uow.read():
        insert(uow, 1)
    assert items(engine) == []


def test_read_translates_database_errors(engine) -> None:
    uow = unit_of_work(engine)
    with pytest.raises(UnavailableError), uow.read():
        uow.session.connection().execute(text("SELECT * FROM missing"))


def test_repositories_are_only_available_inside_a_block(engine) -> None:
    uow = unit_of_work(engine)
    with pytest.raises(RuntimeError):
        _ = uow.session
    with uow.write():
        assert uow.session is not None
    with pytest.raises(RuntimeError):
        _ = uow.session


def test_blocks_cannot_be_nested(engine) -> None:
    uow = unit_of_work(engine)
    with uow.read(), pytest.raises(RuntimeError), uow.write():
        pass
