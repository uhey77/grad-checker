import type { CatalogCurriculum } from "../../domain/entities/courseCatalog.ts";
import type { CatalogCategory } from "../../domain/entities/courseCatalog.ts";
import type { CatalogCourse } from "../../domain/entities/courseCatalog.ts";

export interface CourseCatalog {
  curriculum: CatalogCurriculum;
  categories: CatalogCategory[];
  courses: CatalogCourse[];
}
