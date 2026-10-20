import { SubjectListError } from "../../../../modules/subjects/public.ts";

export function subjectListErrorMessage(error: unknown): string {
  if (error instanceof SubjectListError) {
    if (error.detail) return error.detail;
    if (error.code === "unavailable" || error.code === "invalid-response")
      return "科目一覧に接続できませんでした。時間をおいて再試行してください。";
    return "科目一覧を読み込めませんでした。";
  }
  return error instanceof Error
    ? error.message
    : "科目一覧を読み込めませんでした。";
}
