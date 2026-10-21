import type { SubjectListRepository } from "../queries/SubjectListRepository.ts";
export class ListSubjectProgramsUseCase {
  constructor(private readonly repository: SubjectListRepository) {}
  execute(signal: AbortSignal) {
    return this.repository.listPrograms(signal);
  }
}
