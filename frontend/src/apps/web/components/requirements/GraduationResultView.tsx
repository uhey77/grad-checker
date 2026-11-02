import { useTranslation } from "react-i18next";
import type { GraduationResult } from "../../../../modules/requirements/public.ts";
import { RequirementMatrix } from "./RequirementMatrix.tsx";
import { GraduationOverview } from "./GraduationOverview.tsx";
import { ShortageCourses } from "./ShortageCourses.tsx";
export function GraduationResultView({
  result,
  showOverview = true,
}: {
  result: GraduationResult;
  showOverview?: boolean;
}) {
  const { t } = useTranslation();
  return (
    <div className="graduation-result">
      {showOverview && (
        <GraduationOverview
          key={`${result.curriculum.id}:${result.dataRevision}:${result.evaluatedAt}`}
          result={result}
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
      <h3>{t("科目区分別の単位")}</h3>
      <RequirementMatrix requirements={result.requirements} />
      <ShortageCourses result={result} />
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
