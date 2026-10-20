import type { GradeAttempt } from "../../domain/entities/gradeAttempt.ts";

export interface StudentGrades {
  grades: GradeAttempt[];
  dataRevision: number;
}

export interface GradeSet {
  expectedRevision: number;
  grades: GradeAttempt[];
}
