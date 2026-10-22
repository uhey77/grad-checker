import { useTranslation } from "react-i18next";
import { useId, useState } from "react";
import {
  filterRequirements,
  type GraduationResult,
} from "../../../../modules/requirements/public.ts";
import { ScrollTable } from "../ScrollTable.tsx";
import { CreditsCell } from "../subjects/SubjectCells.tsx";
import { GraduationOverview } from "./GraduationOverview.tsx";
import { CourseRecommendations } from "./CourseRecommendations.tsx";
import { judgmentLabels } from "./labels.ts";
const categoryLabels: Record<string, string> = {
  実学基礎科目合計: "実学基礎",
  専門基礎教育科目合計: "専門基礎",
  専門教育科目合計: "専門教育",
};
export function GraduationResultView({
  result,
  showOverview = true,
}: {
  result: GraduationResult;
  showOverview?: boolean;
}) {
  const { t } = useTranslation();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const conditionsId = useId();
  const categories = result.requirements.filter(
    (row) => row.kind === "classification_total",
  );
  const activeId = categories.some((row) => row.id === selectedId)
    ? selectedId
    : null;
  const requirements = filterRequirements(result.requirements, activeId);
  return (
    <div className="graduation-result">
      {showOverview && (
        <GraduationOverview
          key={`${result.curriculum.id}:${result.dataRevision}:${result.evaluatedAt}`}
          result={result}
          categories={categories}
        />
      )}
      {result.externalAllocations.length > 0 && (
        <details>
          <summary>{t("他学部科目の算入内訳")}</summary>
          <ul>
            {result.externalAllocations.map((row) => (
              <li key={`${row.ruleId}:${row.targetClassificationId}`}>
                {t(
                  "{{value0}}の選択科目：{{value1}}単位を算入 （修得{{value2}}単位、自由科目{{value3}}単位）",
                  {
                    value0: row.targetName,
                    value1: row.creditedCredits,
                    value2: row.earnedCredits,
                    value3: row.freeCredits,
                  },
                )}
              </li>
            ))}
          </ul>
          <p>{t("自由科目の単位は卒業要件に算入しません。")}</p>
        </details>
      )}
      {(result.completionConditions?.length ?? 0) > 0 && (
        <section aria-label={t("単位以外の修了条件")}>
          <h3>{t("単位以外の修了条件（本人申告）")}</h3>
          <ul>
            {result.completionConditions?.map((c) => (
              <li key={c.code}>
                {c.name}：
                {c.status === "met"
                  ? t("達成（本人申告）")
                  : c.status === "not_met"
                    ? t("未達成")
                    : t("未確認・判定保留")}{" "}
                <a href={c.sourceDocument} target="_blank" rel="noreferrer">
                  {t("根拠（{{value0}}）", { value0: c.sourcePages })}
                </a>
              </li>
            ))}
          </ul>
        </section>
      )}
      <h3>{t("条件別判定")}</h3>
      <div
        className="requirement-filters"
        role="group"
        aria-label={t("判定条件の科目区分")}
      >
        {[{ id: null, name: "すべて" }, ...categories].map((category) => (
          <button
            key={category.id ?? "all"}
            type="button"
            aria-pressed={activeId === category.id}
            aria-controls={conditionsId}
            onClick={() => setSelectedId(category.id)}
          >
            {category.id === null
              ? t(category.name)
              : (categoryLabels[category.name] ?? category.name)}
          </button>
        ))}
      </div>
      <div id={conditionsId}>
        <ScrollTable
          label={t("卒業要件の条件別判定")}
          caption={t("条件ごとの必要単位・修得単位・算入単位・不足単位と判定")}
        >
          <thead>
            <tr>
              <th scope="col">{t("条件")}</th>
              <th scope="col">{t("必要")}</th>
              <th scope="col">{t("修得")}</th>
              <th scope="col">{t("算入")}</th>
              <th scope="col">{t("不足")}</th>
              <th scope="col">{t("判定")}</th>
            </tr>
          </thead>
          <tbody>
            {requirements.map((row) => (
              <tr key={row.id}>
                <th scope="row">{row.name}</th>
                <CreditsCell credits={row.requiredCredits} />
                <CreditsCell credits={row.earnedCredits} />
                <CreditsCell credits={row.creditedCredits} />
                <CreditsCell credits={row.shortage} />
                <td>
                  <span className={`judgment-label ${row.result}`}>
                    {t(judgmentLabels[row.result])}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </ScrollTable>
      </div>
      <h3>{t("未修得の必修科目（全区分）")}</h3>
      {result.missingRequiredCourses.length ? (
        <ul>
          {result.missingRequiredCourses.map((course) => (
            <li key={course.courseId}>
              {t("{{value0}}（{{value1}}単位）", {
                value0: course.name,
                value1: course.credits,
              })}
            </li>
          ))}
        </ul>
      ) : (
        <p>{t("未修得の必修科目はありません。")}</p>
      )}
      {(!result.degreeLevel || result.degreeLevel === "bachelor") && (
        <CourseRecommendations recommendations={result.recommendations} />
      )}
      {result.allocations.length > 0 && (
        <details>
          <summary>{t("選択必修から選択への超過換算")}</summary>
          <ul>
            {result.allocations.map((allocation) => (
              <li key={allocation.requirementId}>
                {t("{{value0}}：{{value1}}単位", {
                  value0: result.requirements.find(
                    (row) => row.id === allocation.requirementId,
                  )?.name,
                  value1: allocation.transferredCredits,
                })}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
