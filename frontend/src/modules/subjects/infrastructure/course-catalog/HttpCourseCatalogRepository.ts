import { requestJson } from "../../../../shared/infrastructure/http.ts";
import { CourseCatalogError } from "../../application/errors/CourseCatalogError.ts";
import type { CourseCatalogRepository } from "../../application/ports/CourseCatalogRepository.ts";
import { toCourseCatalog } from "./mappers.ts";

export class HttpCourseCatalogRepository implements CourseCatalogRepository {
  constructor(private readonly base: string) {}
  private request(path: string, signal: AbortSignal): Promise<unknown> {
    return requestJson(
      this.base + path,
      { signal },
      (status, message) => new CourseCatalogError(status, message),
      {
        unreadable: "科目サービスの応答を読み込めません。",
        failed: "科目データを取得できません。",
      },
    );
  }
  async getCatalog(signal: AbortSignal) {
    const [courses, categories] = await Promise.all([
      this.request("/courses", signal),
      this.request("/categories", signal),
    ]);
    return toCourseCatalog(courses, categories);
  }
}
