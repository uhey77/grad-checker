import type { TFunction } from "i18next";

// 状態には原文を保持し、描画時に翻訳することで、表示中のエラーも言語に追従する。
const variableMessages = [
  {
    pattern: /^パスワードは(\d+)〜(\d+)文字で入力してください。$/,
    key: "パスワードは{{min}}〜{{max}}文字で入力してください。",
  },
  {
    pattern: /^履修年度は(\d+)〜(\d+)の整数で入力してください。$/,
    key: "履修年度は{{min}}〜{{max}}の整数で入力してください。",
  },
];
export function translateMessage(message: string, t: TFunction): string {
  for (const { pattern, key } of variableMessages) {
    const match = pattern.exec(message);
    if (match) return t(key, { min: match[1], max: match[2] });
  }
  // 未知のdetailは原文を残す。エラーの意味や必要な対処を推測しない。
  return t(message);
}
