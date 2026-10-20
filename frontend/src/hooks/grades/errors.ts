import {
  minAcademicYear,
  maxAcademicYear,
  type GradeDraftProblem,
} from "../../modules/grades/public.ts";

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
