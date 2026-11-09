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
import type {
  GradeImportOutcome,
  GradeImportPlan,
  ImportedGrade,
} from "../dto/gradeScreenshot.ts";

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

export function groupAttemptsByCourse(
  grades: GradeAttempt[],
): Map<string, GradeAttempt[]> {
  const grouped = new Map<string, GradeAttempt[]>();
  for (const grade of grades) {
    const attempts = grouped.get(grade.courseId) ?? [];
    attempts.push(grade);
    grouped.set(grade.courseId, attempts);
  }
  for (const attempts of grouped.values()) attempts.sort(byKey);
  return grouped;
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

const termOrder = { first: 0, second: 1 } as const;

// 年度・学期の古い順。時期が不明な回次は後ろへ置き、同じ時期では元の順序を保つ。
function byPeriod(
  a: Pick<GradeAttempt, "academicYear" | "termCode">,
  b: Pick<GradeAttempt, "academicYear" | "termCode">,
): number {
  const left = a.academicYear ?? Infinity;
  const right = b.academicYear ?? Infinity;
  if (left !== right) return left < right ? -1 : 1;
  return (
    (a.termCode === null ? 2 : termOrder[a.termCode]) -
    (b.termCode === null ? 2 : termOrder[b.termCode])
  );
}

// 読み取った成績を科目ごとに未保存の全集合へ反映する。
// 同じ年度・学期の回次と時期が不明な既存の回次は読み取った成績で置き換え、
// 時期の異なる既存の回次は再履修の履歴として残す。回次の規則に反する科目は変更しない。
export function planGradeImport(
  grades: GradeAttempt[],
  imported: ImportedGrade[],
): GradeImportPlan {
  const period = (g: Pick<GradeAttempt, "academicYear" | "termCode">) =>
    `${g.academicYear}:${g.termCode}`;
  const byCourse = new Map<string, Map<string, ImportedGrade>>();
  for (const grade of imported) {
    const periods = byCourse.get(grade.courseId) ?? new Map();
    // 同じ時期の行が重複した場合は後の行を使う。
    periods.set(period(grade), grade);
    byCourse.set(grade.courseId, periods);
  }
  const outcomes = new Map<string, GradeImportOutcome>();
  let next = grades;
  for (const [courseId, periods] of byCourse) {
    const existing = attemptsOf(next, courseId);
    const kept = existing.filter(
      (a) => a.academicYear !== null && !periods.has(period(a)),
    );
    const attempts = [...kept, ...periods.values()]
      .sort(byPeriod)
      .map((g, index): GradeAttempt => ({
        courseId,
        attemptNo: index + 1,
        resultStatus: g.resultStatus,
        gradeCode: g.resultStatus === "pending" ? null : g.gradeCode,
        academicYear: g.academicYear,
        termCode: g.termCode,
      }));
    if (!isValidAttemptSequence(attempts)) {
      outcomes.set(courseId, "invalid");
      continue;
    }
    outcomes.set(
      courseId,
      existing.length === 0
        ? "added"
        : sameGrades(existing, attempts)
          ? "unchanged"
          : "updated",
    );
    next = replaceCourse(next, courseId, attempts);
  }
  return { grades: next, outcomes };
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
