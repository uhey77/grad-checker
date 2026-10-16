import { createSubjectListUseCases } from "./application/subject-list/SubjectListUseCases";
import { createCourseCatalogUseCases } from "./application/course-catalog/CourseCatalogUseCases";
import { HttpSubjectListRepository } from "./infrastructure/subject-list/HttpSubjectListRepository";
import { HttpCourseCatalogRepository } from "./infrastructure/course-catalog/HttpCourseCatalogRepository";

export function createSubjectsModule(baseUrl: string) {
  return createSubjectListUseCases(new HttpSubjectListRepository(baseUrl));
}

export function createCourseCatalogModule(baseUrl: string) {
  return createCourseCatalogUseCases(new HttpCourseCatalogRepository(baseUrl));
}
