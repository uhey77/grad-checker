"""ListCoursesUseCaseの処理手順とトランザクション境界。"""

from modules.subjects.grad_checker_subjects.application.errors.course_catalog import (
    CourseCatalogError,
)

from ..course_catalog import CourseCatalogUnitOfWork, CourseFilters, CourseList, matches


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
