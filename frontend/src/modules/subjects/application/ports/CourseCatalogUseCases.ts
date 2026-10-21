import type { GetCourseCatalogUseCase } from "../use_cases/GetCourseCatalogUseCase.ts";

export interface CourseCatalogUseCases {
  readonly getCatalog: Pick<GetCourseCatalogUseCase, "execute">;
}
