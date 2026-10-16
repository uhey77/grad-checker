export type GradeCode = "S" | "A" | "B" | "C" | "D" | "X";
export type ResultStatus = "finalized" | "pending";
export type TermCode = "first" | "second";

// 1科目の1回の履修。未履修は記録なしで表す。
export interface GradeAttempt {
  courseId: string;
  attemptNo: number;
  resultStatus: ResultStatus;
  gradeCode: GradeCode | null;
  academicYear: number | null;
  termCode: TermCode | null;
}

export interface StudentGrades {
  grades: GradeAttempt[];
  dataRevision: number;
}

export interface GradeSet {
  expectedRevision: number;
  grades: GradeAttempt[];
}
