import type { GradeRepository } from "../ports/GradeRepository.ts";

export class GetGradesUseCase {
  constructor(private readonly repository: GradeRepository) {}
  execute(signal?: AbortSignal) {
    return this.repository.getGrades(signal);
  }
}
