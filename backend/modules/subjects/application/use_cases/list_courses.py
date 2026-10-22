"""ListCoursesUseCaseの処理手順とトランザクション境界。"""

from modules.subjects.application.dto.course_catalog import CourseFilters, CourseList
from modules.subjects.application.errors.course_catalog import CourseCatalogError
from modules.subjects.application.services.course_catalog import matches
from modules.subjects.application.uow.course_catalog import CourseCatalogUnitOfWork


class ListCoursesUseCase:
    def __init__(self, uow: CourseCatalogUnitOfWork) -> None:
        self.uow = uow

    def execute(self, curriculum_id: str, filters: CourseFilters) -> CourseList:
        with self.uow.read():
            catalog = self.uow.catalog.get_catalog(curriculum_id)
        if filters.category_id is not None and all(
            category.id != filters.category_id for category in catalog.categories
        ):
            raise CourseCatalogError("unknown_category")
        return CourseList(
            curriculum=catalog.curriculum,
            courses=[course for course in catalog.courses if matches(course, filters)],
        )
