// 業務エラーの日本語メッセージを表示に使い、ない場合は画面ごとの文言にする。
export function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback;
}
