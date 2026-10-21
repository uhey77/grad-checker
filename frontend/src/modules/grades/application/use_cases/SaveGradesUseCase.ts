import type { GradeSet } from "../dto/grades.ts";
import type { GradeRepository } from "../ports/GradeRepository.ts";

export class SaveGradesUseCase {
  constructor(private readonly repository: GradeRepository) {}
  execute(gradeSet: GradeSet, csrf: string, signal?: AbortSignal) {
    return this.repository.saveGrades(gradeSet, csrf, signal);
  }
}
