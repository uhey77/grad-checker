"""このモジュールのRepository・Queryを束ねるSQLiteのUnit of Work実装。"""

from sqlalchemy import Engine

from modules.grades.application.uow.grades import GradeUnitOfWork
from modules.grades.infrastructure.persistence.repositories.grades import (
    SqliteGradeRepository,
)
from modules.grades.infrastructure.persistence.repositories.grades import (
    unavailable as grades_unavailable,
)
from shared.infrastructure.persistence.unit_of_work import SqlUnitOfWork


class SqliteGradeUnitOfWork(SqlUnitOfWork, GradeUnitOfWork):
    def __init__(self, engine: Engine) -> None:
        super().__init__(engine, grades_unavailable)

    @property
    def grades(self) -> SqliteGradeRepository:
        return SqliteGradeRepository(self.session)
