import type { Subject } from "../../domain/subject-list/models";

export const emptyFilters = {
  search: "",
  category: "",
  type: "",
  semester: "",
  faculty: "",
};

export type SubjectFilters = typeof emptyFilters;

export function filterSubjects(
  subjects: Subject[],
  filters: SubjectFilters,
): Subject[] {
  const query = filters.search.trim().normalize("NFKC").toLocaleLowerCase("ja");
  return subjects.filter((subject) => {
    return (
      (!query ||
        subject.name
          .normalize("NFKC")
          .toLocaleLowerCase("ja")
          .includes(query)) &&
      (!filters.category ||
        subject.classificationPath[0]?.id === filters.category) &&
      (!filters.type || subject.subjectType === filters.type) &&
      (!filters.semester ||
        subject.offerings.some((x) => x.termCode === filters.semester)) &&
      (!filters.faculty || subject.facultyName === filters.faculty)
    );
  });
}
