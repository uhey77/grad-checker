import type { CatalogRepository } from "./CatalogRepository";

export function createCatalogUseCases(repository: CatalogRepository) {
  return {
    listPrograms: (signal: AbortSignal) => repository.listPrograms(signal),
    getCatalog: (curriculumId: string, signal: AbortSignal) =>
      repository.getCatalog(curriculumId, signal),
  };
}

export type CatalogUseCases = ReturnType<typeof createCatalogUseCases>;
