import type { SubjectListRepository } from "./SubjectListRepository";

export function createSubjectListUseCases(repository: SubjectListRepository) {
  return {
    listPrograms: (signal: AbortSignal) => repository.listPrograms(signal),
    getSubjectList: (curriculumId: string, signal: AbortSignal) =>
      repository.getSubjectList(curriculumId, signal),
  };
}

export type SubjectListUseCases = ReturnType<typeof createSubjectListUseCases>;
