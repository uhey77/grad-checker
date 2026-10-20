import type { CourseCatalog } from "../../domain/course-catalog/models.ts";
export interface CourseCatalogRepository {
  getCatalog(signal: AbortSignal): Promise<CourseCatalog>;
}
