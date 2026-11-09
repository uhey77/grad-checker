export type GradeScreenshotProblem =
  "not_image" | "too_large" | "unreadable" | "no_rows";

// スクリーンショットから成績を読み取れなかった失敗。表示文言は画面がコードから決める。
export class GradeScreenshotError extends Error {
  constructor(
    readonly problem: GradeScreenshotProblem,
    options?: ErrorOptions,
  ) {
    super(problem, options);
    this.name = "GradeScreenshotError";
  }
}
