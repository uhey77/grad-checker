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
  result: Pick<GraduationResult, "result" | "total" | "warnings">;
  categories: RequirementResult[];
}) {
  return (
    <>
      <p className={`judgment ${result.result}`} role="status">
        卒業要件：{judgmentLabels[result.result]}
      </p>
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
