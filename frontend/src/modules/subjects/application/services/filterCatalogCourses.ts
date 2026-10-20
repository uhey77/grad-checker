import type { CatalogCourse } from "../../domain/course-catalog/models.ts";

export const emptyCatalogFilters = {
  search: "",
  categoryId: "",
  faculty: "",
  department: "",
  semester: "",
};

export type CatalogFilters = typeof emptyCatalogFilters;

function normalize(value: string): string {
  return value.normalize("NFKC").toLocaleLowerCase("ja");
}

// 複数条件はANDで適用する。区分は子孫分類を含み、学期は科目の開講学期を表す。
export function filterCatalogCourses(
  courses: CatalogCourse[],
  filters: CatalogFilters,
): CatalogCourse[] {
  const query = normalize(filters.search.trim());
  return courses.filter(
    (course) =>
      (!query ||
        normalize(course.name).includes(query) ||
        normalize(course.code).includes(query)) &&
      (!filters.categoryId ||
        !!course.placement?.classificationPath.some(
          (item) => item.id === filters.categoryId,
        )) &&
      (!filters.faculty || course.offeringFacultyName === filters.faculty) &&
      (!filters.department ||
        course.offeringDepartmentName === filters.department) &&
      (!filters.semester ||
        course.offerings.some((item) => item.termCode === filters.semester)),
  );
}

export function facultyOptions(courses: CatalogCourse[]): string[] {
  return [...new Set(courses.map((course) => course.offeringFacultyName))].sort(
    (a, b) => a.localeCompare(b, "ja"),
  );
}

export function departmentOptions(
  courses: CatalogCourse[],
  faculty: string,
): string[] {
  const names = courses
    .filter((course) => !faculty || course.offeringFacultyName === faculty)
    .map((course) => course.offeringDepartmentName)
    .filter((name): name is string => name !== null);
  return [...new Set(names)].sort((a, b) => a.localeCompare(b, "ja"));
}
