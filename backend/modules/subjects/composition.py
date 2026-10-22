"""この業務モジュールの具体実装を操作別UseCaseへ注入する。"""

from collections.abc import Callable

from sqlalchemy import Engine

from modules.subjects.infrastructure.persistence.unit_of_work import (
    SqliteCourseCatalogUnitOfWork,
    SqliteSubjectDataUnitOfWork,
    SqliteSubjectListUnitOfWork,
)
from modules.subjects.public import (
    GetSubjectListUseCase,
    ImportSubjectDataUseCase,
    ListCategoriesUseCase,
    ListCoursesUseCase,
    ListSubjectProgramsUseCase,
)


def build_use_cases(engine: Engine) -> dict[str, Callable[[], object]]:
    return {
        "list_courses": lambda: ListCoursesUseCase(
            SqliteCourseCatalogUnitOfWork(engine)
        ),
        "list_categories": lambda: ListCategoriesUseCase(
            SqliteCourseCatalogUnitOfWork(engine)
        ),
        "get_subject_list": lambda: GetSubjectListUseCase(
            SqliteSubjectListUnitOfWork(engine)
        ),
        "list_subject_programs": lambda: ListSubjectProgramsUseCase(
            SqliteSubjectListUnitOfWork(engine)
        ),
    }


def build_import_use_case(engine: Engine) -> ImportSubjectDataUseCase:
    return ImportSubjectDataUseCase(SqliteSubjectDataUnitOfWork(engine))
