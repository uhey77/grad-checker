import {
  allowsRetake,
  isValidAttemptSequence,
  courseStatus,
  maxAcademicYear,
  minAcademicYear,
  type CourseStatus,
} from "../../domain/services/attempts.ts";
import type { GradeAttempt } from "../../domain/entities/gradeAttempt.ts";
import type { GradeCode, TermCode } from "../../domain/value_objects/grade.ts";

// 未保存の成績全集合を編集する純粋関数。非表示の科目の成績も保持する。
export type GradeChoice = GradeCode | "pending";

function byKey(a: GradeAttempt, b: GradeAttempt): number {
  return a.courseId === b.courseId
    ? a.attemptNo - b.attemptNo
    : a.courseId < b.courseId
      ? -1
      : 1;
}

export function attemptsOf(
  grades: GradeAttempt[],
  courseId: string,
): GradeAttempt[] {
  return grades.filter((g) => g.courseId === courseId).sort(byKey);
}

function replaceCourse(
  grades: GradeAttempt[],
  courseId: string,
  attempts: GradeAttempt[],
): GradeAttempt[] {
  return [...grades.filter((g) => g.courseId !== courseId), ...attempts].sort(
    byKey,
  );
}

function updateAttempt(
  grades: GradeAttempt[],
  courseId: string,
  attemptNo: number,
  patch: Partial<GradeAttempt>,
): GradeAttempt[] {
  return grades.map((g) =>
    g.courseId === courseId && g.attemptNo === attemptNo
      ? { ...g, ...patch }
      : g,
  );
}

// 未履修の科目は1回目を作り、""を選ぶと1回目だけの科目を未履修へ戻す。
export function chooseGrade(
  grades: GradeAttempt[],
  courseId: string,
  attemptNo: number,
  choice: GradeChoice | "",
): GradeAttempt[] {
  const attempts = attemptsOf(grades, courseId);
  if (choice === "")
    return attempts.length === 1 && attemptNo === 1
      ? replaceCourse(grades, courseId, [])
      : grades;
  const values = {
    resultStatus: choice === "pending" ? "pending" : "finalized",
    gradeCode: choice === "pending" ? null : choice,
  } as const;
  if (attempts.length === 0 && attemptNo === 1)
    return replaceCourse(grades, courseId, [
      { courseId, attemptNo: 1, academicYear: null, termCode: null, ...values },
    ]);
  return updateAttempt(grades, courseId, attemptNo, values);
}

export function setAttemptPeriod(
  grades: GradeAttempt[],
  courseId: string,
  attemptNo: number,
  academicYear: number | null,
  termCode: TermCode | null,
): GradeAttempt[] {
  return updateAttempt(grades, courseId, attemptNo, { academicYear, termCode });
}

export function canAddRetake(attempts: GradeAttempt[]): boolean {
  const latest = attempts.at(-1);
  return latest !== undefined && allowsRetake(latest);
}

export function addRetake(
  grades: GradeAttempt[],
  courseId: string,
): GradeAttempt[] {
  const attempts = attemptsOf(grades, courseId);
  if (!canAddRetake(attempts)) return grades;
  return replaceCourse(grades, courseId, [
    ...attempts,
    {
      courseId,
      attemptNo: attempts.length + 1,
      resultStatus: "pending",
      gradeCode: null,
      academicYear: null,
      termCode: null,
    },
  ]);
}

export function removeLatestAttempt(
  grades: GradeAttempt[],
  courseId: string,
): GradeAttempt[] {
  return replaceCourse(
    grades,
    courseId,
    attemptsOf(grades, courseId).slice(0, -1),
  );
}

export function sameGrades(a: GradeAttempt[], b: GradeAttempt[]): boolean {
  if (a.length !== b.length) return false;
  const left = [...a].sort(byKey);
  const right = [...b].sort(byKey);
  return left.every(
    (g, index) =>
      g.courseId === right[index].courseId &&
      g.attemptNo === right[index].attemptNo &&
      g.resultStatus === right[index].resultStatus &&
      g.gradeCode === right[index].gradeCode &&
      g.academicYear === right[index].academicYear &&
      g.termCode === right[index].termCode,
  );
}

// 保存前に画面で直せる入力の誤りを示す。回次の業務ルールは保存時にサーバーでも検証する。
export type GradeDraftProblem =
  "invalid_academic_year" | "invalid_attempt_sequence";

export function draftProblem(grades: GradeAttempt[]): GradeDraftProblem | null {
  if (
    grades.some(
      (g) =>
        g.academicYear !== null &&
        (!Number.isSafeInteger(g.academicYear) ||
          g.academicYear < minAcademicYear ||
          g.academicYear > maxAcademicYear),
    )
  )
    return "invalid_academic_year";
  const courses = new Set(grades.map((g) => g.courseId));
  for (const courseId of courses) {
    const attempts = attemptsOf(grades, courseId);
    if (!isValidAttemptSequence(attempts)) return "invalid_attempt_sequence";
  }
  return null;
}

export const emptyGradeFilters = { status: "", year: "", term: "" };
export type GradeFilters = typeof emptyGradeFilters;

// 修得状況と、本人が履修した年度・学期で絞り込む。年度と学期は同じ回次で一致させる。
export function matchesGradeFilters(
  attempts: GradeAttempt[],
  filters: GradeFilters,
): boolean {
  if (
    filters.status &&
    courseStatus(attempts) !== (filters.status as CourseStatus)
  )
    return false;
  if (!filters.year && !filters.term) return true;
  return attempts.some(
    (a) =>
      (!filters.year || String(a.academicYear) === filters.year) &&
      (!filters.term || a.termCode === filters.term),
  );
}

export function takenYears(grades: GradeAttempt[]): number[] {
  return [
    ...new Set(
      grades
        .map((g) => g.academicYear)
        .filter((year): year is number => year !== null),
    ),
  ].sort((a, b) => b - a);
}
