// UIと他モジュールが利用する科目モジュールの公開契約。
export type {
  Program,
  Offering,
  Subject,
  SubjectList,
} from "./domain/subject-list/models";
export type { SubjectListUseCases } from "./application/ports/SubjectListUseCases.ts";
export {
  emptyFilters,
  filterSubjects,
  type SubjectFilters,
} from "./application/services/filterSubjects.ts";
export {
  sortSubjects,
  isSubjectSortOrder,
  type SubjectSortOrder,
} from "./application/services/sortSubjects.ts";
export { SubjectListError } from "./application/errors/SubjectListError.ts";
export type {
  CatalogCategory,
  CatalogCourse,
  CatalogCurriculum,
  CourseCatalog,
  CoursePlacement,
  CourseType,
} from "./domain/course-catalog/models.ts";
export type { CourseCatalogUseCases } from "./application/ports/CourseCatalogUseCases.ts";
export {
  emptyCatalogFilters,
  filterCatalogCourses,
  facultyOptions,
  departmentOptions,
  type CatalogFilters,
} from "./application/services/filterCatalogCourses.ts";
export { CourseCatalogError } from "./application/errors/CourseCatalogError.ts";

export { ListSubjectProgramsUseCase } from "./application/use_cases/ListSubjectProgramsUseCase.ts";
export { GetSubjectListUseCase } from "./application/use_cases/GetSubjectListUseCase.ts";

export { GetCourseCatalogUseCase } from "./application/use_cases/GetCourseCatalogUseCase.ts";
