// 学生向け科目一覧の取得失敗。statusは外部APIのHTTPステータス（通信失敗は0）。
export class CourseCatalogError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "CourseCatalogError";
  }
}
