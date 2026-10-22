// UIと他モジュールが利用する科目モジュールの公開契約。
export type { Program, Subject } from "./domain/entities/subject.ts";
export type { Offering } from "./domain/value_objects/offering.ts";
export type { SubjectList } from "./application/dto/subjectList.ts";
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
} from "./domain/entities/courseCatalog.ts";
export type { CourseCatalog } from "./application/dto/courseCatalog.ts";
export type {
  CoursePlacement,
  CourseType,
} from "./domain/value_objects/course.ts";
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
