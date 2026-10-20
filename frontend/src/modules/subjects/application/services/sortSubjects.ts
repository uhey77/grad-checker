import type { Subject } from "../../domain/subject-list/models.ts";

export const subjectSortOrders = [
  "handbook",
  "name",
  "credits-ascending",
  "credits-descending",
  "semester",
] as const;
export type SubjectSortOrder = (typeof subjectSortOrders)[number];

export function isSubjectSortOrder(value: string): value is SubjectSortOrder {
  return subjectSortOrders.some((order) => order === value);
}

const names = new Intl.Collator("ja", { numeric: true, sensitivity: "base" });

// 同順位は取得時の便覧順を保ち、元の一覧を変更しない。
export function sortSubjects(
  subjects: Subject[],
  order: SubjectSortOrder,
): Subject[] {
  if (order === "handbook") return [...subjects];
  return [...subjects].sort((a, b) => {
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
