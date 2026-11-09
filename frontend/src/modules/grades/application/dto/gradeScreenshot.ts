import type { GradeAttempt } from "../../domain/entities/gradeAttempt.ts";
import type {
  GradeCode,
  ResultStatus,
  TermCode,
} from "../../domain/value_objects/grade.ts";

// 照合に使う科目。公式の科目名を原文のまま渡す。
export interface ScreenshotCourse {
  courseId: string;
  name: string;
  // 本人課程の科目表にある科目。同名の課程外の科目より優先して照合する。
  inCurriculum: boolean;
}

// スクリーンショットの1行から読み取った成績。反映前に本人が確認する。
export interface ScreenshotGradeRow {
  // OCRで読み取った行の原文。
  line: string;
  // 照合できた科目の候補。Ⅰ・Ⅱなどの番号違いを含む。
  candidateCourseIds: string[];
  // 候補から自動で選んだ科目。番号を判別できない場合はnull。
  courseId: string | null;
  // 読み違いや番号違いの可能性があり、本人の確認が必要な行。
  needsReview: boolean;
  // 評価を読み取れなかった場合はnull。
  resultStatus: ResultStatus | null;
  gradeCode: GradeCode | null;
  academicYear: number | null;
  termCode: TermCode | null;
}

// 本人が反映を選んだ1回分の成績。
export interface ImportedGrade {
  courseId: string;
  resultStatus: ResultStatus;
  gradeCode: GradeCode | null;
  academicYear: number | null;
  termCode: TermCode | null;
}

export type GradeImportOutcome = "added" | "updated" | "unchanged" | "invalid";

export interface GradeImportPlan {
  // 反映後の未保存の成績全集合。
  grades: GradeAttempt[];
  outcomes: ReadonlyMap<string, GradeImportOutcome>;
}

export type ScreenshotReadProgress =
  { stage: "preparing" } | { stage: "recognizing"; ratio: number };
