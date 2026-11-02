import type { Judgment } from "../../../../modules/requirements/public.ts";

// 判定のpass/failを画面の表記へ変換する。
export const judgmentLabels: Record<Judgment, string> = {
  pass: "達成",
  pending: "判定保留",
  fail: "未達成",
};
