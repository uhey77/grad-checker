import type { CatalogRepository } from "../../application/course-catalog/CatalogRepository";
import type { CatalogDto, ProgramDto } from "./dto";
import { toCatalog, toProgram } from "./mappers";

export class HttpCatalogRepository implements CatalogRepository {
  constructor(private readonly baseUrl: string) {}

  async listPrograms(signal: AbortSignal) {
    const body = await this.request<ProgramDto[]>(
      `${this.baseUrl}/programs`,
      signal,
    );
    return body.map(toProgram);
  }

  async getCatalog(curriculumId: string, signal: AbortSignal) {
    const body = await this.request<CatalogDto>(
      `${this.baseUrl}/${encodeURIComponent(curriculumId)}`,
      signal,
    );
    return toCatalog(body);
  }

  private async request<T>(url: string, signal: AbortSignal): Promise<T> {
    try {
      const response = await fetch(url, { signal });
      const body: unknown = await response.json();
      if (!response.ok) {
        const detail =
          typeof body === "object" && body !== null && "detail" in body
            ? body.detail
            : null;
        throw new Error(
          typeof detail === "string"
            ? detail
            : "科目一覧を読み込めませんでした。",
        );
      }
      return body as T;
    } catch (error) {
      if (error instanceof TypeError || error instanceof SyntaxError)
        throw new Error(
          "科目一覧に接続できませんでした。時間をおいて再試行してください。",
        );
      throw error;
    }
  }
}
