import { useId, useState } from "react";
import {
  filterRequirements,
  type GraduationResult,
} from "../../modules/requirements/public.ts";
import { ScrollTable } from "../ScrollTable";
import { CreditsCell } from "../subjects/SubjectCells";
import { GraduationInfographic } from "./GraduationInfographic";

const label = { pass: "達成", fail: "未達成" };
const categoryLabels: Record<string, string> = {
  実学基礎科目合計: "実学基礎",
  専門基礎教育科目合計: "専門基礎",
  専門教育科目合計: "専門教育",
};

export function GraduationResultView({ result }: { result: GraduationResult }) {
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
      <p className={`judgment ${result.result}`} role="status">
        卒業要件：{label[result.result]}
      </p>
      <GraduationInfographic
        key={`${result.curriculum.id}:${result.dataRevision}:${result.evaluatedAt}`}
        result={result}
      />
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
                    {label[row.result]}
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
