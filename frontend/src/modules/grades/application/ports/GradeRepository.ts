import type { GradeSet, StudentGrades } from "../../domain/models.ts";
export interface GradeRepository {
  getGrades(signal?: AbortSignal): Promise<StudentGrades>;
  saveGrades(
    gradeSet: GradeSet,
    csrf: string,
    signal?: AbortSignal,
  ): Promise<StudentGrades>;
}
