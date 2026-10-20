"""科目カタログの検索条件との照合。"""

from ..dto.course_catalog import CatalogCourse, CourseFilters


def matches(course: CatalogCourse, filters: CourseFilters) -> bool:
    if filters.category_id is not None and (
        course.placement is None
        or all(
            c.id != filters.category_id for c in course.placement.classification_path
        )
    ):
        return False
    if filters.faculty is not None and course.offering_faculty_name != filters.faculty:
        return False
    if (
        filters.department is not None
        and course.offering_department_name != filters.department
    ):
        return False
    if filters.semester is not None and all(
        offering.term_code != filters.semester for offering in course.offerings
    ):
        return False
    if filters.q is not None:
        keyword = filters.q.casefold()
        return keyword in course.name.casefold() or keyword in course.code.casefold()
    return True
