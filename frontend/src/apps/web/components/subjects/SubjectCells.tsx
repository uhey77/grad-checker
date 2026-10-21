import type { ReactNode } from "react";
import type {
  CourseType,
  Offering,
} from "../../../../modules/subjects/public.ts";
import {
  joinLabels,
  offeringLabels,
  sharedAcrossYears,
  subjectTypeLabels,
} from "./labels.ts";

// 科目一覧と成績入力で同じ科目を同じ形で表示するための表のセル。

export function SubjectNameCell({
  name,
  code,
}: {
  name: string;
  code: string;
}) {
  return (
    <th scope="row">
      <span className="subject-name">{name}</span>
      <small>{code}</small>
    </th>
  );
}

export function SubjectTypeBadge({ type }: { type: CourseType }) {
  return <span className={`badge ${type}`}>{subjectTypeLabels[type]}</span>;
}

// 分類の最上位を見出しに、下位の科目群を補足に表示する。
export function ClassificationCell({
  path,
  emptyLabel,
  children,
}: {
  path: { name: string }[];
  emptyLabel: string;
  children?: ReactNode;
}) {
  return (
    <td className="classification">
      <span>{path[0]?.name ?? emptyLabel}</span>
      {path.length > 1 ? (
        <small>{joinLabels(path.slice(1).map((item) => item.name))}</small>
      ) : null}
      {children}
    </td>
  );
}

export function OfferingsCell({ offerings }: { offerings: Offering[] }) {
  return (
    <td className="offerings">
      <span>{offeringLabels(offerings).join("・") || "記載なし"}</span>
      {sharedAcrossYears(offerings) ? (
        <small className="shared-years">学年共通開講</small>
      ) : null}
    </td>
  );
}

export function ProviderCell({
  facultyName,
  departmentName,
  specializationName,
  teachingTypeLabel,
}: {
  facultyName: string;
  departmentName: string | null;
  specializationName: string | null;
  teachingTypeLabel: string;
}) {
  return (
    <td>
      <span>{facultyName}</span>
      <small>
        {joinLabels([departmentName, specializationName, teachingTypeLabel])}
      </small>
    </td>
  );
}

export function CreditsCell({ credits }: { credits: number }) {
  return <td className="credits">{credits}</td>;
}
