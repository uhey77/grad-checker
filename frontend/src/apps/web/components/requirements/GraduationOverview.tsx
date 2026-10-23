import { useTranslation } from "react-i18next";
import type {
  GraduationResult,
  RequirementResult,
} from "../../../../modules/requirements/public.ts";
import { GraduationInfographic } from "./GraduationInfographic.tsx";
export function GraduationOverview({
  result,
  categories,
}: {
  result: Pick<
    GraduationResult,
    "result" | "total" | "warnings" | "degreeLevel" | "completionConditions"
  >;
  categories: RequirementResult[];
}) {
  const { t } = useTranslation();
  return (
    <>
      <GraduationInfographic result={result} categories={categories} />
      <dl className="credit-summary">
        <div>
          <dt>{t("必要単位")}</dt>
          <dd>{result.total.requiredCredits}</dd>
        </div>
        <div>
          <dt>{t("修得単位")}</dt>
          <dd>{result.total.earnedCredits}</dd>
        </div>
        <div>
          <dt>{t("算入単位")}</dt>
          <dd>{result.total.creditedCredits}</dd>
        </div>
        <div>
          <dt>{t("不足単位")}</dt>
          <dd>{result.total.shortage}</dd>
        </div>
      </dl>
      {result.degreeLevel && result.degreeLevel !== "bachelor" && (
        <p className="source-note" role="note">
          {t(
            "本人申告に基づく参考判定です。正式な修了認定は大学が行います。単位条件の達成だけでは修了を意味しません。",
          )}
        </p>
      )}
      {result.warnings.includes("provisional_external_allocation") && (
        <p className="source-note" role="note">
          {t(
            "他学部科目は取得順に算入し、同時期の科目は卒業要件を満たしやすい配分で計算しています。 配分方法は本アプリの仮定のため、大学の扱いと異なる場合があります。",
          )}
        </p>
      )}
    </>
  );
}
