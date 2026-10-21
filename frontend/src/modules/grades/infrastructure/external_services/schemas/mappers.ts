import { createDtoReader } from "../../../../../shared/infrastructure/dtoReader.ts";
import { GradeError } from "../../../application/errors/GradeError.ts";
import { gradeCodes } from "../../../domain/services/attempts.ts";
import type { GradeAttempt } from "../../../domain/entities/gradeAttempt.ts";
import type { GradeCode } from "../../../domain/value_objects/grade.ts";
import type {
  GradeSet,
  StudentGrades,
} from "../../../application/dto/grades.ts";

const { invalid, record, text, integer, nullableInteger } = createDtoReader(
  () => {
    throw new GradeError(502, "成績データを読み込めません。");
  },
);

function toAttempt(data: unknown): GradeAttempt {
  const value = record(data);
  const status = value.result_status;
  const code = value.grade_code;
  const term = value.term_code;
  if (
    (status !== "finalized" && status !== "pending") ||
    (status === "finalized") !== (code !== null) ||
    (code !== null && !gradeCodes.includes(code as GradeCode)) ||
    (term !== null && term !== "first" && term !== "second")
  )
    return invalid();
  return {
    courseId: text(value.course_id),
    attemptNo: integer(value.attempt_no, 1),
    resultStatus: status,
    gradeCode: code as GradeCode | null,
    academicYear: nullableInteger(value.academic_year),
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
