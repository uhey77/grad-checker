import { GradeError } from "../application/GradeUseCases.ts";
import { gradeCodes } from "../domain/attempts.ts";
import type {
  GradeAttempt,
  GradeCode,
  GradeSet,
  StudentGrades,
} from "../domain/models.ts";

function invalid(): never {
  throw new GradeError(502, "成績データを読み込めません。");
}
function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value))
    return invalid();
  return value as Record<string, unknown>;
}
function integer(value: unknown, minimum: number): number {
  if (
    typeof value !== "number" ||
    !Number.isSafeInteger(value) ||
    value < minimum
  )
    return invalid();
  return value;
}

function toAttempt(data: unknown): GradeAttempt {
  const value = record(data);
  const status = value.result_status;
  const code = value.grade_code;
  const term = value.term_code;
  if (
    (status !== "finalized" && status !== "pending") ||
    (status === "finalized") !== (code !== null) ||
    (code !== null && !gradeCodes.includes(code as GradeCode)) ||
    (term !== null && term !== "first" && term !== "second") ||
    typeof value.course_id !== "string" ||
    !value.course_id
  )
    return invalid();
  return {
    courseId: value.course_id,
    attemptNo: integer(value.attempt_no, 1),
    resultStatus: status,
    gradeCode: code as GradeCode | null,
    academicYear:
      value.academic_year === null ? null : integer(value.academic_year, 1),
    termCode: term,
  };
}

export function toStudentGrades(data: unknown): StudentGrades {
  const value = record(data);
  if (!Array.isArray(value.grades)) return invalid();
  return {
    grades: value.grades.map(toAttempt),
    dataRevision: integer(value.data_revision, 0),
  };
}

export function toGradeSetDto(gradeSet: GradeSet) {
  return {
    expected_revision: gradeSet.expectedRevision,
    grades: gradeSet.grades.map((g) => ({
      course_id: g.courseId,
      attempt_no: g.attemptNo,
      result_status: g.resultStatus,
      grade_code: g.gradeCode,
      academic_year: g.academicYear,
      term_code: g.termCode,
    })),
  };
}
