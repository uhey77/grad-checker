import type { Course } from "../../domain/course-catalog/models";

export const emptyFilters = {
  search: "",
  category: "",
  type: "",
  semester: "",
  faculty: "",
};

export type CatalogFilters = typeof emptyFilters;

export function filterCourses(
  courses: Course[],
  filters: CatalogFilters,
): Course[] {
  const query = filters.search.trim().normalize("NFKC").toLocaleLowerCase("ja");
  return courses.filter((course) => {
    return (
      (!query ||
        course.name
          .normalize("NFKC")
          .toLocaleLowerCase("ja")
          .includes(query)) &&
      (!filters.category ||
        course.classificationPath[0]?.id === filters.category) &&
      (!filters.type || course.courseType === filters.type) &&
      (!filters.semester ||
        course.offerings.some((x) => x.termCode === filters.semester)) &&
      (!filters.faculty || course.facultyName === filters.faculty)
    );
  });
}
