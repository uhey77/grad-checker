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
export { GradeUseCases, GradeError } from "./application/GradeUseCases.ts";
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
} from "./application/gradeDraft.ts";
