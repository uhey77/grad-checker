import {
  type SubjectSortOrder,
  type Offering,
} from "../../../../modules/subjects/public.ts";

// 画面をまたいで同じ値を同じ表記にするため、表示ラベルと区切りをここに集約する。

export const subjectTypeLabels = {
  required: "必修",
  selective: "選択必修",
  elective: "選択",
};

// 開講学期・履修学期で共通の学期名。
export const termLabels = {
  first: "前期",
  second: "後期",
};

// 分類の階層や開講元の内訳などの区切り。
export function joinLabels(parts: (string | null | undefined)[]): string {
  return parts.filter(Boolean).join(" / ");
}

interface ProgramNames {
  facultyName: string;
  departmentName?: string | null;
  specializationName: string | null;
  courseName: string | null;
}

// 課程は学部・学科・専攻・コース名で表す。便覧名・版・確認状態は表示しない。
export function programLabel(program: ProgramNames): string {
  return [
    program.facultyName,
    program.departmentName,
    program.specializationName,
    program.courseName,
  ]
    .filter(Boolean)
    .join(" ／ ");
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
  const order = Object.keys(termLabels);
  return [...years]
    .sort(([a], [b]) => a - b)
    .map(([year, terms]) => {
      const labels = [
        ...order.filter((term) => terms.has(term)),
        ...[...terms].filter((term) => !order.includes(term)),
      ].map((term) => termLabels[term as keyof typeof termLabels] ?? term);
      return `${year}年次${labels.join("・")}`;
    });
}

// 便覧注記で学年共通開講とされた科目。
export function sharedAcrossYears(offerings: Offering[]): boolean {
  return offerings.some((offering) =>
    offering.sourceNote?.includes("学年共通"),
  );
}
