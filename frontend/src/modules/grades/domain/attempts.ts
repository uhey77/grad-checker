import type { GradeAttempt, GradeCode } from "./models.ts";

export const gradeCodes: readonly GradeCode[] = ["S", "A", "B", "C", "D", "X"];
export const failingGradeCodes: readonly GradeCode[] = ["D", "X"];
export const minAcademicYear = 1900;
export const maxAcademicYear = 2100;

export type CourseStatus =
  "earned" | "failed" | "absent" | "pending" | "not-taken";

// 再履修できるのは確定した不合格（D・未受験X）の後だけ。合格・未確定の後は追加しない。
export function allowsRetake(attempt: GradeAttempt): boolean {
  return (
    attempt.resultStatus === "finalized" &&
    attempt.gradeCode !== null &&
    failingGradeCodes.includes(attempt.gradeCode)
  );
}

// 合格は常に最新回次になるため、最新回次から科目の修得状況を決める。
export function courseStatus(attempts: GradeAttempt[]): CourseStatus {
  const latest = attempts.reduce<GradeAttempt | null>(
    (current, attempt) =>
      current === null || attempt.attemptNo > current.attemptNo
        ? attempt
        : current,
    null,
  );
  if (latest === null) return "not-taken";
  if (latest.resultStatus === "pending") return "pending";
  if (latest.gradeCode === "D") return "failed";
  if (latest.gradeCode === "X") return "absent";
  return "earned";
}
