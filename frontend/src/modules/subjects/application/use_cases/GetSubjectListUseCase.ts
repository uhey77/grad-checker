import type { SubjectListRepository } from "../queries/SubjectListRepository.ts";
export class GetSubjectListUseCase {
  constructor(private readonly repository: SubjectListRepository) {}
  execute(curriculumId: string, signal: AbortSignal) {
    return this.repository.getSubjectList(curriculumId, signal);
  }
}
