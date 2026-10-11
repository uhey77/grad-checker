import {
  type SubjectSortOrder,
  type Program,
  type Offering,
} from "../../modules/subjects/public.ts";

export const subjectTypeLabels = {
  required: "必修",
  selective: "選択必修",
  elective: "選択",
};

export function programLabel(program: Program): string {
  return (
    [program.specializationName, program.courseName]
      .filter(Boolean)
      .join(" / ") || program.facultyName
  );
}

export const subjectSortLabels: Record<SubjectSortOrder, string> = {
  handbook: "便覧順",
  name: "科目名順",
  "credits-ascending": "単位数の少ない順",
  "credits-descending": "単位数の多い順",
  semester: "開講学年・学期順",
};

export function offeringLabels(offerings: Offering[]): string[] {
  const years = new Map<number, Set<string>>();
  for (const offering of offerings) {
    const year = Math.ceil(offering.semesterOrder / 2);
    const terms = years.get(year) ?? new Set<string>();
    terms.add(offering.termCode);
    years.set(year, terms);
  }
  return [...years]
    .sort(([a], [b]) => a - b)
    .map(([year, terms]) => {
      const labels = [
        ...(terms.has("first") ? ["前期"] : []),
        ...(terms.has("second") ? ["後期"] : []),
        ...[...terms].filter((term) => term !== "first" && term !== "second"),
      ];
      return `${year}年次${labels.join("・")}`;
    });
}
