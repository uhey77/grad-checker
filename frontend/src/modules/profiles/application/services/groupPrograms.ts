import type { ProgramOption } from "../../domain/entities/program.ts";

export type ProgramGroup = "undergraduate" | "graduate" | "other";

export function selectablePrograms(
  programs: readonly ProgramOption[],
): ProgramOption[] {
  return programs.filter(
    (program) => !program.completionPolicy?.unresolvedReasons.length,
  );
}

// 東京工科大学の学部・大学院案内の掲載順。未知の所属は名称順で後ろに表示する。
// https://jyuken.teu.ac.jp/gakubu/index.html
// https://www.teu.ac.jp/grad/gaiyou/index.html
const faculties = [
  "コンピュータサイエンス学部",
  "メディア学部",
  "工学部",
  "応用生物学部",
  "デザイン学部",
  "医療保健学部",
  "バイオ・情報メディア研究科",
  "工学研究科",
  "デザイン研究科",
  "医療技術学研究科",
];
const departments = [
  "看護学科",
  "臨床工学科",
  "リハビリテーション学科",
  "臨床検査学科",
  "機械工学科",
  "電気電子工学科",
  "応用化学科",
];
const specializations = [
  "先進情報専攻",
  "社会情報専攻",
  "理学療法学専攻",
  "作業療法学専攻",
  "言語聴覚学専攻",
  "バイオニクス専攻",
  "コンピュータサイエンス専攻",
  "メディアサイエンス専攻",
  "サステイナブル工学専攻",
  "デザイン専攻",
  "臨床検査学専攻",
];
const courses = [
  "情報基盤コース",
  "人間情報コース",
  "人工知能コース",
  "メディアコンテンツコース",
  "メディア技術コース",
  "メディア社会コース",
  "生命医薬コース",
  "地球環境コース",
  "食品コース",
  "化粧品コース",
  "視覚デザインコース",
  "情報デザインコース",
  "工業デザインコース",
  "空間デザインコース",
  "看護師資格のみ",
  "看護師・保健師資格",
  "修士課程",
  "修士課程（英語プログラム）",
  "博士後期課程",
];
const collator = new Intl.Collator("ja");

function compareNames(
  a: string | null,
  b: string | null,
  order: string[],
): number {
  if (a === b) return 0;
  if (a === null) return -1;
  if (b === null) return 1;
  const aIndex = order.indexOf(a),
    bIndex = order.indexOf(b);
  return (
    (aIndex < 0 ? order.length : aIndex) -
      (bIndex < 0 ? order.length : bIndex) || collator.compare(a, b)
  );
}

function groupOf(program: ProgramOption): ProgramGroup {
  const degree = program.completionPolicy?.degreeLevel;
  if (degree === "bachelor") return "undergraduate";
  if (degree === "master" || degree === "doctoral") return "graduate";
  if (program.facultyName.endsWith("学部")) return "undergraduate";
  if (program.facultyName.endsWith("研究科")) return "graduate";
  return "other";
}

export function groupPrograms(
  programs: readonly ProgramOption[],
): Record<ProgramGroup, ProgramOption[]> {
  const groups: Record<ProgramGroup, ProgramOption[]> = {
    undergraduate: [],
    graduate: [],
    other: [],
  };
  for (const program of programs) groups[groupOf(program)].push(program);
  for (const group of Object.values(groups)) {
    group.sort(
      (a, b) =>
        compareNames(a.facultyName, b.facultyName, faculties) ||
        compareNames(a.departmentName, b.departmentName, departments) ||
        compareNames(
          a.specializationName,
          b.specializationName,
          specializations,
        ) ||
        compareNames(a.courseName, b.courseName, courses) ||
        collator.compare(a.curriculumName, b.curriculumName) ||
        collator.compare(a.curriculumId, b.curriculumId),
    );
  }
  return groups;
}
