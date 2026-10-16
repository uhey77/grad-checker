import type { CourseCatalog } from "../../domain/course-catalog/models.ts";

// 本人課程から見た科目一覧と分類を取得する契約。本人課程はセッションから決まる。
export interface CourseCatalogRepository {
  getCatalog(signal: AbortSignal): Promise<CourseCatalog>;
}

export function createCourseCatalogUseCases(
  repository: CourseCatalogRepository,
) {
  return {
    getCatalog: (signal: AbortSignal) => repository.getCatalog(signal),
  };
}

export type CourseCatalogUseCases = ReturnType<
  typeof createCourseCatalogUseCases
>;
