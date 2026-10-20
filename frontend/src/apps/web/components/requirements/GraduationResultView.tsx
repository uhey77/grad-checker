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
          <summary>他学部科目の算入内訳</summary>
          <ul>
            {result.externalAllocations.map((row) => (
              <li key={`${row.ruleId}:${row.targetClassificationId}`}>
                {row.targetName}の選択科目：{row.creditedCredits}単位を算入
                （修得{row.earnedCredits}単位、自由科目{row.freeCredits}単位）
              </li>
            ))}
          </ul>
          <p>自由科目の単位は卒業要件に算入しません。</p>
        </details>
      )}
      {(result.completionConditions?.length ?? 0) > 0 && (
        <section aria-label="単位以外の修了条件">
          <h3>単位以外の修了条件（本人申告）</h3>
          <ul>
            {result.completionConditions?.map((c) => (
              <li key={c.code}>
                {c.name}：
                {c.status === "met"
                  ? "達成（本人申告）"
                  : c.status === "not_met"
                    ? "未達成"
                    : "未確認・判定保留"}{" "}
                <a href={c.sourceDocument} target="_blank" rel="noreferrer">
                  根拠（{c.sourcePages}）
                </a>
              </li>
            ))}
          </ul>
        </section>
      )}
      <h3>条件別判定</h3>
      <div
        className="requirement-filters"
        role="group"
        aria-label="判定条件の科目区分"
      >
        {[{ id: null, name: "すべて" }, ...categories].map((category) => (
          <button
            key={category.id ?? "all"}
            type="button"
            aria-pressed={activeId === category.id}
            aria-controls={conditionsId}
            onClick={() => setSelectedId(category.id)}
          >
            {categoryLabels[category.name] ?? category.name}
          </button>
        ))}
      </div>
      <div id={conditionsId}>
        <ScrollTable
          label="卒業要件の条件別判定"
          caption="条件ごとの必要単位・修得単位・算入単位・不足単位と判定"
        >
          <thead>
            <tr>
              <th scope="col">条件</th>
              <th scope="col">必要</th>
              <th scope="col">修得</th>
              <th scope="col">算入</th>
              <th scope="col">不足</th>
              <th scope="col">判定</th>
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
                    {judgmentLabels[row.result]}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </ScrollTable>
      </div>
      <h3>未修得の必修科目（全区分）</h3>
      {result.missingRequiredCourses.length ? (
        <ul>
          {result.missingRequiredCourses.map((course) => (
            <li key={course.courseId}>
              {course.name}（{course.credits}単位）
            </li>
          ))}
        </ul>
      ) : (
        <p>未修得の必修科目はありません。</p>
      )}
      {(!result.degreeLevel || result.degreeLevel === "bachelor") && (
        <CourseRecommendations recommendations={result.recommendations} />
      )}
      {result.allocations.length > 0 && (
        <details>
          <summary>選択必修から選択への超過換算</summary>
          <ul>
            {result.allocations.map((allocation) => (
              <li key={allocation.requirementId}>
                {
                  result.requirements.find(
                    (row) => row.id === allocation.requirementId,
                  )?.name
                }
                ：{allocation.transferredCredits}単位
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
