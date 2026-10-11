import type { Course } from "../../domain/course-catalog/models";

export const catalogSortOrders = [
  "handbook",
  "name",
  "credits-ascending",
  "credits-descending",
  "semester",
] as const;
export type CatalogSortOrder = (typeof catalogSortOrders)[number];

export function isCatalogSortOrder(value: string): value is CatalogSortOrder {
  return catalogSortOrders.some((order) => order === value);
}

const names = new Intl.Collator("ja", { numeric: true, sensitivity: "base" });

// 同順位は取得時の便覧順を保ち、元の一覧を変更しない。
export function sortCourses(
  courses: Course[],
  order: CatalogSortOrder,
): Course[] {
  if (order === "handbook") return [...courses];
  return [...courses].sort((a, b) => {
    switch (order) {
      case "name":
        return names.compare(a.name, b.name);
      case "credits-ascending":
        return a.credits - b.credits;
      case "credits-descending":
        return b.credits - a.credits;
      case "semester": {
        const first = Math.min(...a.offerings.map((x) => x.semesterOrder));
        const second = Math.min(...b.offerings.map((x) => x.semesterOrder));
        return first === second ? 0 : first < second ? -1 : 1;
      }
    }
  });
}
