import type { CourseCatalogRepository } from "../queries/CourseCatalogRepository.ts";
export class GetCourseCatalogUseCase {
  constructor(private readonly repository: CourseCatalogRepository) {}
  execute(signal: AbortSignal) {
    return this.repository.getCatalog(signal);
  }
}
