"""ListCategoriesUseCaseの処理手順とトランザクション境界。"""

from modules.subjects.application.dto.course_catalog import CategoryList
from modules.subjects.application.uow.course_catalog import CourseCatalogUnitOfWork


class ListCategoriesUseCase:
    def __init__(self, uow: CourseCatalogUnitOfWork) -> None:
        self.uow = uow

    def execute(self, curriculum_id: str) -> CategoryList:
        with self.uow.read():
            catalog = self.uow.catalog.get_catalog(curriculum_id)
        return CategoryList(
            curriculum=catalog.curriculum, categories=catalog.categories
        )
