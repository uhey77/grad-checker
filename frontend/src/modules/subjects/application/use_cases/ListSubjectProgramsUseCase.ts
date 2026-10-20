import type { SubjectListRepository } from "../ports/SubjectListRepository.ts";
export class ListSubjectProgramsUseCase {
  constructor(private readonly repository: SubjectListRepository) {}
  execute(signal: AbortSignal) {
    return this.repository.listPrograms(signal);
  }
}
