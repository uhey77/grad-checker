import type { SavedCheck } from "../../../../modules/requirements/public.ts";
import { gradeChoiceLabels } from "../grades/labels.ts";
import { ScrollTable } from "../ScrollTable.tsx";
import { ErrorState, LoadingState } from "../StatusPanels.tsx";
import { GraduationResultView } from "./GraduationResultView.tsx";
import { checkedAtLabel } from "./labels.ts";

type DetailState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; check: SavedCheck };

// 保存済みの過去の判定を、当時の日時・課程・規則版とともに最新の判定と区別して表示する。
export function PastCheckView({
  detail,
  retry,
  showLatest,
}: {
  detail: DetailState;
  retry: () => void;
  showLatest: () => void;
}) {
  const back = (
    <button type="button" className="primary-button" onClick={showLatest}>
      最新の判定に戻る
    </button>
  );
  if (detail.status === "loading")
    return (
      <div className="past-check">
        <LoadingState>過去の判定を読み込んでいます…</LoadingState>
        {back}
      </div>
    );
  if (detail.status === "error")
    return (
      <div className="past-check">
        <ErrorState
          title="過去の判定を表示できませんでした"
          message={detail.message}
          actionLabel="再試行"
          onAction={retry}
        />
        {back}
      </div>
    );
  const { check } = detail;
  return (
    <div className="past-check">
      <div className="past-check-banner" role="note">
        <strong className="past-check-badge">過去の判定</strong>
        <dl>
          <div>
            <dt>判定日時</dt>
            <dd>
              <time dateTime={check.createdAt}>
                {checkedAtLabel(check.createdAt)}
              </time>
            </dd>
          </div>
          <div>
            <dt>課程</dt>
            <dd>{check.result.curriculum.name}</dd>
          </div>
          <div>
            <dt>規則版</dt>
            <dd>{check.result.curriculum.revision}</dd>
          </div>
        </dl>
        <p>
          保存時の成績と判定結果です。その後に成績や要件が更新されても、この内容は変わりません。
        </p>
        {back}
      </div>
      <details className="past-check-input">
        <summary>判定に使った成績（{check.input.grades.length}件）</summary>
        {check.input.grades.length ? (
          <ScrollTable
            label="判定に使った成績"
            caption="判定時に保存されていた成績"
          >
            <thead>
              <tr>
                <th scope="col">科目</th>
                <th scope="col">回次</th>
                <th scope="col">成績</th>
              </tr>
            </thead>
            <tbody>
              {check.input.grades.map((grade) => (
                <tr key={`${grade.courseId}:${grade.attemptNo}`}>
                  <th scope="row">{grade.courseName ?? "科目名なし"}</th>
                  <td>{grade.attemptNo}</td>
                  <td>{gradeChoiceLabels[grade.gradeCode ?? "pending"]}</td>
                </tr>
              ))}
            </tbody>
          </ScrollTable>
        ) : (
          <p>判定時に保存されていた成績はありません。</p>
        )}
      </details>
      <GraduationResultView result={check.result} />
    </div>
  );
}
