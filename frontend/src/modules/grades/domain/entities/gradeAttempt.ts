import type { GradeCode } from "../value_objects/grade.ts";
import type { ResultStatus } from "../value_objects/grade.ts";
import type { TermCode } from "../value_objects/grade.ts";

// 1科目の1回の履修。未履修は記録なしで表す。
export interface GradeAttempt {
  courseId: string;
  attemptNo: number;
  resultStatus: ResultStatus;
  gradeCode: GradeCode | null;
  academicYear: number | null;
  termCode: TermCode | null;
}
