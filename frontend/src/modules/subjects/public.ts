// UIと他モジュールが利用する科目モジュールの公開契約。
export type {
  Program,
  Offering,
  Subject,
  SubjectList,
} from "./domain/subject-list/models";
export type { SubjectListUseCases } from "./application/subject-list/SubjectListUseCases";
export {
  emptyFilters,
  filterSubjects,
  type SubjectFilters,
} from "./application/subject-list/filterSubjects.ts";
export {
  sortSubjects,
  isSubjectSortOrder,
  type SubjectSortOrder,
} from "./application/subject-list/sortSubjects.ts";
export { SubjectListError } from "./application/errors/SubjectListError.ts";
export type {
  CatalogCategory,
  CatalogCourse,
  CatalogCurriculum,
  CourseCatalog,
  CoursePlacement,
  CourseType,
} from "./domain/course-catalog/models.ts";
export type { CourseCatalogUseCases } from "./application/course-catalog/CourseCatalogUseCases.ts";
export {
  emptyCatalogFilters,
  filterCatalogCourses,
  facultyOptions,
  departmentOptions,
  type CatalogFilters,
} from "./application/course-catalog/filterCatalogCourses.ts";
export { CourseCatalogError } from "./application/errors/CourseCatalogError.ts";
