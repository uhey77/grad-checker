import { createSubjectListUseCases } from "./application/subject-list/SubjectListUseCases";
import { HttpSubjectListRepository } from "./infrastructure/subject-list/HttpSubjectListRepository";

export function createSubjectsModule(baseUrl: string) {
  return createSubjectListUseCases(new HttpSubjectListRepository(baseUrl));
}
