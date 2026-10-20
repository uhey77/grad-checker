import { ListSubjectProgramsUseCase } from "./application/use_cases/ListSubjectProgramsUseCase.ts";
import { GetSubjectListUseCase } from "./application/use_cases/GetSubjectListUseCase.ts";
import { GetCourseCatalogUseCase } from "./application/use_cases/GetCourseCatalogUseCase.ts";
import type { SubjectListUseCases } from "./application/ports/SubjectListUseCases.ts";
import type { CourseCatalogUseCases } from "./application/ports/CourseCatalogUseCases.ts";
import { HttpSubjectListRepository } from "./infrastructure/external_services/subject-list/HttpSubjectListRepository.ts";
import { HttpCourseCatalogRepository } from "./infrastructure/external_services/course-catalog/HttpCourseCatalogRepository.ts";
export function createSubjectsModule(base: string): SubjectListUseCases {
  const repository = new HttpSubjectListRepository(base);
  return {
    listPrograms: new ListSubjectProgramsUseCase(repository),
    getSubjectList: new GetSubjectListUseCase(repository),
  };
}
export function createCourseCatalogModule(base: string): CourseCatalogUseCases {
  return {
    getCatalog: new GetCourseCatalogUseCase(
      new HttpCourseCatalogRepository(base),
    ),
  };
}
