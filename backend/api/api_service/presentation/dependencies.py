"""内部呼出しごとのPythonリソース管理。"""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlmodel import Session


def get_session(request: Request) -> Iterator[Session]:
    # commitはユースケース側で明示する。終了時に未commitの変更は破棄される。
    with Session(request.app.state.database_engine) as session:
        yield session


SessionDependency = Annotated[Session, Depends(get_session)]
