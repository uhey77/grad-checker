import { CourseCatalogError } from "../../application/errors/CourseCatalogError.ts";
import type { CourseCatalogRepository } from "../../application/course-catalog/CourseCatalogUseCases.ts";
import { toCourseCatalog } from "./mappers.ts";

export class HttpCourseCatalogRepository implements CourseCatalogRepository {
  constructor(private readonly base: string) {}
  private async request(path: string, signal: AbortSignal): Promise<unknown> {
    try {
      const response = await fetch(this.base + path, {
        credentials: "same-origin",
        cache: "no-store",
        signal,
      });
      let data: unknown;
      try {
        data = await response.json();
      } catch {
        if (signal.aborted) throw signal.reason;
        throw new CourseCatalogError(
          response.ok ? 502 : response.status,
          "科目サービスの応答を読み込めません。",
        );
      }
      if (!response.ok) {
        const detail =
          data &&
          typeof data === "object" &&
          "detail" in data &&
          typeof data.detail === "string"
            ? data.detail
            : "科目データを取得できません。";
        throw new CourseCatalogError(response.status, detail);
      }
      return data;
    } catch (error) {
      if (signal.aborted || error instanceof CourseCatalogError) throw error;
      throw new CourseCatalogError(
        0,
        "サーバーへ接続できません。時間をおいて再試行してください。",
      );
    }
  }
  async getCatalog(signal: AbortSignal) {
    const [courses, categories] = await Promise.all([
      this.request("/courses", signal),
      this.request("/categories", signal),
    ]);
    return toCourseCatalog(courses, categories);
  }
}
