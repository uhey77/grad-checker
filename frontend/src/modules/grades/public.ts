// UIと他モジュールが利用する成績モジュールの公開契約。
export type {
  GradeAttempt,
  GradeCode,
  GradeSet,
  ResultStatus,
  StudentGrades,
  TermCode,
} from "./domain/models.ts";
export {
  allowsRetake,
  courseStatus,
  failingGradeCodes,
  gradeCodes,
  maxAcademicYear,
  minAcademicYear,
  type CourseStatus,
} from "./domain/attempts.ts";
export type { GradeUseCases } from "./application/ports/GradeUseCases.ts";
export { GradeError } from "./application/errors/GradeError.ts";
export {
  addRetake,
  attemptsOf,
  canAddRetake,
  chooseGrade,
  draftProblem,
  emptyGradeFilters,
  matchesGradeFilters,
  removeLatestAttempt,
  sameGrades,
  setAttemptPeriod,
  takenYears,
  type GradeChoice,
  type GradeFilters,
  type GradeDraftProblem,
} from "./application/services/gradeDraft.ts";

export { GetGradesUseCase } from "./application/use_cases/GetGradesUseCase.ts";
export { SaveGradesUseCase } from "./application/use_cases/SaveGradesUseCase.ts";
