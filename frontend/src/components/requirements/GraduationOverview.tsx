import type {
  GraduationResult,
  RequirementResult,
} from "../../modules/requirements/public.ts";
import { GraduationInfographic } from "./GraduationInfographic";
import { judgmentLabels } from "./labels";

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
  return (
    <>
      <p className={`judgment ${result.result}`} role="status">
        {result.degreeLevel && result.degreeLevel !== "bachelor"
          ? "修了要件"
          : "卒業要件"}
        ：{judgmentLabels[result.result]}
      </p>
      {result.degreeLevel && result.degreeLevel !== "bachelor" && (
        <p className="source-note" role="note">
          本人申告に基づく参考判定です。正式な修了認定は大学が行います。単位条件の達成だけでは修了を意味しません。
        </p>
      )}
      <GraduationInfographic result={result} categories={categories} />
      <dl className="credit-summary">
        <div>
          <dt>必要単位</dt>
          <dd>{result.total.requiredCredits}</dd>
        </div>
        <div>
          <dt>修得単位</dt>
          <dd>{result.total.earnedCredits}</dd>
        </div>
        <div>
          <dt>算入単位</dt>
          <dd>{result.total.creditedCredits}</dd>
        </div>
        <div>
          <dt>不足単位</dt>
          <dd>{result.total.shortage}</dd>
        </div>
      </dl>
      {result.warnings.includes("provisional_external_allocation") && (
        <p className="source-note" role="note">
          他学部科目は取得順に算入し、同時期の科目は卒業要件を満たしやすい配分で計算しています。
          配分方法は本アプリの仮定のため、大学の扱いと異なる場合があります。
        </p>
      )}
    </>
  );
}
