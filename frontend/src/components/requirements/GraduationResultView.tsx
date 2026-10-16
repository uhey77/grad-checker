import type { GraduationResult } from "../../modules/requirements/public.ts";
import { ScrollTable } from "../ScrollTable";
import { CreditsCell } from "../subjects/SubjectCells";

const label = { pass: "達成", fail: "未達成" };

export function GraduationResultView({ result }: { result: GraduationResult }) {
  return (
    <div className="graduation-result">
      <p className={`judgment ${result.result}`} role="status">
        卒業要件：{label[result.result]}
      </p>
      <p>
        {result.curriculum.name} · 判定日時：
        {new Date(result.evaluatedAt).toLocaleString("ja-JP")}
      </p>
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
          {result.requirements.map((row) => (
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
      <h3>未修得の必修科目</h3>
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
      <p className="source-note">
        出典：{result.curriculum.sourceDocument}（
        {result.curriculum.sourcePages}）
      </p>
    </div>
  );
}
