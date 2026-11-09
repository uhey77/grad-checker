import {
  maxAcademicYear,
  minAcademicYear,
} from "../../domain/services/attempts.ts";
import type { GradeCode, TermCode } from "../../domain/value_objects/grade.ts";
import type {
  ScreenshotCourse,
  ScreenshotGradeRow,
} from "../dto/gradeScreenshot.ts";

// OCRで読み取った成績表の文字列を、課程の科目と照合して行ごとの成績へ変換する。
// OCRは文字間に空白を入れ、Ⅰ・Ⅱなどの番号を「|」「ll」や別の漢字に読み違えるため、
// 科目名は番号を除いた部分のあいまい一致で照合し、番号は直後の文字から推定する。

const romanNumerals = "ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ";

interface CourseVariant {
  courseId: string;
  numeral: number | null;
}

interface CourseGroup {
  // 番号を除き、NFKC・小文字化・空白除去した科目名。
  base: string;
  variants: CourseVariant[];
}

// 科目名末尾のⅠ・Ⅱや数字を番号として分ける。
function splitNumeral(name: string): { base: string; numeral: number | null } {
  const trimmed = name.trim();
  const match = /\s*([ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]|[0-9０-９])$/.exec(trimmed);
  if (!match || match.index === 0) return { base: trimmed, numeral: null };
  const symbol = match[1];
  const roman = romanNumerals.indexOf(symbol);
  return {
    base: trimmed.slice(0, match.index),
    numeral: roman >= 0 ? roman + 1 : Number(symbol.normalize("NFKC")),
  };
}

// 照合用に正規化し、元の文字列の位置へ戻せる対応表を作る。
function compact(text: string): { value: string; origin: number[] } {
  let value = "";
  const origin: number[] = [];
  for (let index = 0; index < text.length; index++) {
    const normalized = text[index].normalize("NFKC").toLowerCase();
    for (const char of normalized) {
      if (/\s/.test(char)) continue;
      value += char;
      origin.push(index);
    }
  }
  return { value, origin };
}

function groupCourses(courses: ScreenshotCourse[]): CourseGroup[] {
  const groups = new Map<string, CourseGroup>();
  for (const course of courses) {
    const { base, numeral } = splitNumeral(course.name);
    const key = compact(base).value;
    if (!key) continue;
    const group = groups.get(key) ?? { base: key, variants: [] };
    group.variants.push({ courseId: course.courseId, numeral });
    groups.set(key, group);
  }
  for (const group of groups.values())
    group.variants.sort((a, b) => (a.numeral ?? 0) - (b.numeral ?? 0));
  return [...groups.values()];
}

// 読み違いを許す文字数。短い科目名は他の科目と取り違えやすいため完全一致に限る。
function allowedDistance(length: number): number {
  return length <= 3 ? 0 : Math.floor(length / 4);
}

interface Match {
  distance: number;
  start: number;
  end: number;
}

// 文字列中の任意の位置に対する編集距離が最小となる部分を探す（Sellersの方法）。
export function approximateMatch(pattern: string, text: string): Match | null {
  const m = pattern.length;
  const n = text.length;
  if (m === 0 || n === 0) return null;
  let previous = new Array<number>(n + 1).fill(0);
  let previousStart = Array.from({ length: n + 1 }, (_, j) => j);
  for (let i = 1; i <= m; i++) {
    const current = new Array<number>(n + 1);
    const currentStart = new Array<number>(n + 1);
    current[0] = i;
    currentStart[0] = 0;
    for (let j = 1; j <= n; j++) {
      const substitution =
        previous[j - 1] + (pattern[i - 1] === text[j - 1] ? 0 : 1);
      const deletion = previous[j] + 1;
      const insertion = current[j - 1] + 1;
      if (substitution <= deletion && substitution <= insertion) {
        current[j] = substitution;
        currentStart[j] = previousStart[j - 1];
      } else if (deletion <= insertion) {
        current[j] = deletion;
        currentStart[j] = previousStart[j];
      } else {
        current[j] = insertion;
        currentStart[j] = currentStart[j - 1];
      }
    }
    previous = current;
    previousStart = currentStart;
  }
  let best: Match | null = null;
  for (let j = 1; j <= n; j++)
    if (best === null || previous[j] < best.distance)
      best = { distance: previous[j], start: previousStart[j], end: j };
  return best;
}

interface GroupMatch extends Match {
  group: CourseGroup;
}

function findCourse(line: string, groups: CourseGroup[]): GroupMatch | null {
  let best: GroupMatch | null = null;
  for (const group of groups) {
    const match = approximateMatch(group.base, line);
    if (!match || match.distance > allowedDistance(group.base.length)) continue;
    // 一致した文字数が多い科目を優先し、短い科目名が長い科目名の一部に一致するのを避ける。
    const score = group.base.length - match.distance;
    const bestScore = best ? best.group.base.length - best.distance : -1;
    if (
      score > bestScore ||
      (score === bestScore && match.distance < best!.distance)
    )
      best = { ...match, group };
  }
  return best;
}

// 科目名の直後にある番号を推定する。空白の後の数字は単位数と区別できないため使わない。
function numeralAfter(rest: string): {
  numeral: number | null;
  length: number;
} {
  const spaced = /^\s/.test(rest);
  const trimmed = rest.trimStart();
  const skipped = rest.length - trimmed.length;
  const roman = /^[ⅠⅡⅢⅣ]/.exec(trimmed);
  if (roman)
    return {
      numeral: romanNumerals.indexOf(roman[0]) + 1,
      length: skipped + 1,
    };
  const strokes = /^[|Il!｜ｌＩ]+(?![A-Za-z])/.exec(trimmed);
  if (strokes && strokes[0].length <= 3)
    return { numeral: strokes[0].length, length: skipped + strokes[0].length };
  if (!spaced) {
    const digit = /^[1-9](?![0-9])/.exec(trimmed);
    if (digit) return { numeral: Number(digit[0]), length: 1 };
  }
  return { numeral: null, length: 0 };
}

function chooseVariant(
  variants: CourseVariant[],
  numeral: number | null,
): string | null {
  if (variants.length === 1) return variants[0].courseId;
  // 同じ番号の科目が複数ある場合は推測で選ばない。
  const matches = variants.filter((v) => v.numeral === numeral);
  return matches.length === 1 ? matches[0].courseId : null;
}

const gradeTokens = new Set<string>(["S", "A", "B", "C", "D", "X"]);
const pendingWords = /履修中|未確定|未評価|評価前/;
const firstTermWords = /前期|前其|前学期|春学期|春期/;
const secondTermWords = /後期|後其|後学期|秋学期|秋期/;

function tokens(text: string): string[] {
  return text
    .normalize("NFKC")
    .split(/\s+/)
    .map((token) =>
      token.replace(/^[|.,:;()[\]（）「」]+|[|.,:;()[\]（）「」]+$/g, ""),
    )
    .filter(Boolean);
}

function gradeIn(text: string): GradeCode | null {
  for (const token of tokens(text)) {
    const upper = token.toUpperCase();
    if (upper.length === 1 && gradeTokens.has(upper)) return upper as GradeCode;
  }
  return null;
}

function yearIn(text: string): number | null {
  for (const token of tokens(text)) {
    const match = /^((?:19|20)[0-9]{2})(?:年度?)?([^0-9A-Za-z]*)$/.exec(token);
    if (!match) continue;
    const year = Number(match[1]);
    if (year >= minAcademicYear && year <= maxAcademicYear) return year;
  }
  return null;
}

function termIn(text: string): TermCode | null {
  const value = text.replace(/\s+/g, "");
  const first = firstTermWords.exec(value)?.index ?? -1;
  const second = secondTermWords.exec(value)?.index ?? -1;
  if (first < 0 && second < 0) return null;
  if (second < 0 || (first >= 0 && first < second)) return "first";
  return "second";
}

function parseLine(
  line: string,
  tiers: CourseGroup[][],
): ScreenshotGradeRow | null {
  const { value, origin } = compact(line);
  // 本人課程の科目表にある科目を優先し、一致しない場合だけ課程外の科目と照合する。
  let found: GroupMatch | null = null;
  for (const groups of tiers) {
    found = findCourse(value, groups);
    if (found) break;
  }
  let before = line;
  let after = "";
  let candidateCourseIds: string[] = [];
  let courseId: string | null = null;
  let needsReview = false;
  if (found) {
    const startIndex = origin[found.start];
    const endIndex = origin[found.end - 1] + 1;
    const numeral = numeralAfter(line.slice(endIndex));
    before = line.slice(0, startIndex);
    after = line.slice(endIndex + numeral.length);
    candidateCourseIds = found.group.variants.map((v) => v.courseId);
    courseId = chooseVariant(found.group.variants, numeral.numeral);
    // 読み違いを補正した科目と、番号違いの科目がある行は本人に確認してもらう。
    needsReview =
      found.distance > 0 ||
      found.group.variants.length > 1 ||
      courseId === null;
  }
  const outside = `${before} ${after}`;
  const pending = pendingWords.test(outside.replace(/\s+/g, ""));
  const gradeCode = pending ? null : (gradeIn(after) ?? gradeIn(before));
  if (!found && gradeCode === null && !pending) return null;
  return {
    line: line.trim(),
    candidateCourseIds,
    courseId,
    needsReview,
    resultStatus: pending ? "pending" : gradeCode ? "finalized" : null,
    gradeCode,
    academicYear: yearIn(after) ?? yearIn(before),
    termCode: termIn(after) ?? termIn(before),
  };
}

// 科目と照合できた行と、成績らしい値を含むが照合できなかった行を返す。
export function parseGradeScreenshotText(
  text: string,
  courses: ScreenshotCourse[],
): ScreenshotGradeRow[] {
  const tiers = [
    groupCourses(courses.filter((course) => course.inCurriculum)),
    groupCourses(courses),
  ];
  return text
    .split(/\r?\n/)
    .filter((line) => line.trim())
    .map((line) => parseLine(line, tiers))
    .filter((row): row is ScreenshotGradeRow => row !== null);
}
