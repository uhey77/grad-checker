import type { Judgment } from "../../../../modules/requirements/public.ts";

// 判定のpass/failを画面の表記へ変換する。
export const judgmentLabels: Record<Judgment, string> = {
  pass: "達成",
  pending: "判定保留",
  fail: "未達成",
};

// 判定日時を閲覧環境の時刻で表示する。
export function checkedAtLabel(iso: string, language = "ja"): string {
  return new Intl.DateTimeFormat(language === "en" ? "en-US" : "ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(iso));
}
