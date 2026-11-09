import {
  minAcademicYear,
  maxAcademicYear,
  type GradeDraftProblem,
  type GradeScreenshotProblem,
} from "../../../../modules/grades/public.ts";

// スクリーンショットを読み取れなかった理由を、画面の日本語メッセージへ変換する。
export function gradeScreenshotProblemMessage(
  problem: GradeScreenshotProblem,
): string {
  const messages: Record<GradeScreenshotProblem, string> = {
    not_image: "画像ファイルを選択してください。",
    too_large: "画像が大きすぎます。20MB以下の画像を選択してください。",
    unreadable:
      "画像を読み取れませんでした。別の画像で再度お試しいただくか、手動で入力してください。",
    no_rows:
      "成績の行を読み取れませんでした。成績表の部分を大きく写した画像でお試しください。",
  };
  return messages[problem];
}

// 業務上の入力エラーを、画面の日本語メッセージへ変換する。
export function gradeDraftProblemMessage(
  problem: GradeDraftProblem | null,
): string | null {
  if (problem === null) return null;
  const messages: Record<GradeDraftProblem, string> = {
    invalid_academic_year: `履修年度は${minAcademicYear}〜${maxAcademicYear}の整数で入力してください。`,
    invalid_attempt_sequence:
      "再履修の前の回次は不合格（D・X）にしてください。",
  };
  return messages[problem];
}
