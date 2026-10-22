import type { CourseCatalog } from "../dto/courseCatalog.ts";
export interface CourseCatalogRepository {
  getCatalog(signal: AbortSignal): Promise<CourseCatalog>;
}
