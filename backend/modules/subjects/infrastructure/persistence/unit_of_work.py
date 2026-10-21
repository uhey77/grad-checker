"""このモジュールのRepository・Queryを束ねるSQLiteのUnit of Work実装。"""

from sqlalchemy import Engine

from modules.subjects.application.uow.course_catalog import CourseCatalogUnitOfWork
from modules.subjects.application.uow.subject_data_import import SubjectDataUnitOfWork
from modules.subjects.application.uow.subject_list import SubjectListUnitOfWork
from modules.subjects.infrastructure.persistence.queries.course_catalog import (
    SqliteCourseCatalogRepository,
)
from modules.subjects.infrastructure.persistence.queries.course_catalog import (
    unavailable as course_catalog_unavailable,
)
from modules.subjects.infrastructure.persistence.queries.subject_list import (
    SqliteSubjectListRepository,
)
from modules.subjects.infrastructure.persistence.queries.subject_list import (
    unavailable as subject_list_unavailable,
)
from modules.subjects.infrastructure.persistence.repositories.subject_data import (
    SqliteSubjectDataStore,
)
from modules.subjects.infrastructure.persistence.repositories.subject_data import (
    unavailable as subject_data_import_unavailable,
)
from shared.infrastructure.persistence.unit_of_work import SqlUnitOfWork


class SqliteSubjectListUnitOfWork(SqlUnitOfWork, SubjectListUnitOfWork):
    def __init__(self, engine: Engine) -> None:
        super().__init__(engine, subject_list_unavailable)

    @property
    def subject_list(self) -> SqliteSubjectListRepository:
        return SqliteSubjectListRepository(self.session)


class SqliteSubjectDataUnitOfWork(SqlUnitOfWork, SubjectDataUnitOfWork):
    def __init__(self, engine: Engine) -> None:
        super().__init__(engine, subject_data_import_unavailable)

    @property
    def subject_data(self) -> SqliteSubjectDataStore:
        return SqliteSubjectDataStore(self.session)


class SqliteCourseCatalogUnitOfWork(SqlUnitOfWork, CourseCatalogUnitOfWork):
    def __init__(self, engine: Engine) -> None:
        super().__init__(engine, course_catalog_unavailable)

    @property
    def catalog(self) -> SqliteCourseCatalogRepository:
        return SqliteCourseCatalogRepository(self.session)
