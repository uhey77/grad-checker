import { useTranslation } from "react-i18next";
import {
  buildRequirementMatrix,
  type RequirementResult,
} from "../../../../modules/requirements/public.ts";
import { ScrollTable } from "../ScrollTable.tsx";
import { judgmentLabels } from "./labels.ts";

const columns = [
  { kind: "classification_total", label: "合計" },
  { kind: "required_courses", label: "必修" },
  { kind: "elective_total", label: "選択" },
  { kind: "selective_group", label: "選択必修" },
] as const;

const suffixes = {
  total: /$/,
  classification_total: /合計$/,
  required_courses: /の必修$/,
  elective_total: /の選択$/,
  selective_group: /の選択必修$/,
  subminimum: /の内訳最低単位$|[0-9０-９]+単位以上$/,
};

export function requirementCategoryName(requirement: RequirementResult) {
  return (
    requirement.name.replace(suffixes[requirement.kind], "") || requirement.name
  );
}

export function RequirementMatrix({
  requirements,
}: {
  requirements: RequirementResult[];
}) {
  const { t } = useTranslation();
  const rows = buildRequirementMatrix(requirements);
  return (
    <ScrollTable
      label={t("科目区分別の単位")}
      caption={t("科目区分ごとの合計・必修・選択・選択必修と最低単位の条件")}
      className="requirement-matrix"
    >
      <colgroup>
        <col className="requirement-category-column" />
        {columns.map(({ kind }) => (
          <col key={kind} />
        ))}
      </colgroup>
      <thead>
        <tr>
          <th scope="col">{t("科目区分")}</th>
          {columns.map(({ kind, label }) => (
            <th key={kind} scope="col">
              {t(label)}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, index) => (
          <tr
            key={row.id}
            className={[
              row.requirement.kind === "classification_total"
                ? "requirement-category-total"
                : "",
              row.depth === 0 && index > 0 ? "requirement-group-start" : "",
            ]
              .filter(Boolean)
              .join(" ")}
          >
            <th scope="row" style={{ paddingInlineStart: 12 + row.depth * 20 }}>
              {requirementCategoryName(row.requirement)}
              {row.requirement.kind === "subminimum" &&
                t("（最低{{value0}}単位）", {
                  value0: row.requirement.requiredCredits,
                })}
            </th>
            {columns.map(({ kind }) => (
              <td key={kind}>
                {row.cells[kind]?.length ? (
                  row.cells[kind]!.map((condition) => (
                    <div
                      key={condition.id}
                      className="requirement-credit"
                      role="group"
                      aria-label={condition.name}
                    >
                      {row.cells[kind]!.length > 1 && (
                        <span className="requirement-credit-name">
                          {condition.name}
                        </span>
                      )}
                      <span className="requirement-credit-value">
                        {condition.creditedCredits} /{" "}
                        {condition.requiredCredits}
                      </span>
                      <span className="sr-only">
                        {t(judgmentLabels[condition.result])}
                      </span>
                    </div>
                  ))
                ) : (
                  <span
                    className="requirement-empty"
                    aria-label={t("条件の記載なし")}
                  >
                    —
                  </span>
                )}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </ScrollTable>
  );
}
