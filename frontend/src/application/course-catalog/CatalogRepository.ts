import type { Catalog, Program } from "../../domain/course-catalog/models";

// 通信方法を問わず、科目一覧の取得に必要な契約。
export interface CatalogRepository {
  listPrograms(signal: AbortSignal): Promise<Program[]>;
  getCatalog(curriculumId: string, signal: AbortSignal): Promise<Catalog>;
}
