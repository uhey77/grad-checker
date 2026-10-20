import type { CheckPage } from "../../../../modules/requirements/public.ts";
import { ScrollTable } from "../ScrollTable.tsx";
import { EmptyState, ErrorState, LoadingState } from "../StatusPanels.tsx";
import { CreditsCell } from "../subjects/SubjectCells.tsx";
import { checkedAtLabel, judgmentLabels } from "./labels.ts";

type PageState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: CheckPage };

// 本人の判定履歴を新しい順に表示し、過去の判定を選ぶ。共有・公開の操作は設けない。
export function CheckHistory({
  page,
  pageSize,
  selectedId,
  select,
  showPage,
  retry,
}: {
  page: PageState;
  pageSize: number;
  selectedId: string | null;
  select: (id: string) => void;
  showPage: (offset: number) => void;
  retry: () => void;
}) {
  return (
    <section className="check-history" aria-label="判定履歴">
      <h3>判定履歴</h3>
      {page.status === "loading" ? (
        <LoadingState>判定履歴を読み込んでいます…</LoadingState>
      ) : page.status === "error" ? (
        <ErrorState
          title="判定履歴を取得できませんでした"
          message={page.message}
          actionLabel="判定履歴を再取得"
          onAction={retry}
        />
      ) : page.data.totalCount === 0 ? (
        <EmptyState
          title="判定履歴はまだありません"
          message="要件チェックを実行すると、判定結果が履歴に保存されます。"
          actionLabel="判定履歴を再取得"
          onAction={retry}
        />
      ) : page.data.checks.length === 0 ? (
        <EmptyState
          title="このページに判定履歴はありません"
          message="履歴の件数が変わった可能性があります。"
          actionLabel="最新の履歴を表示"
          onAction={() => showPage(0)}
        />
      ) : (
        <>
          <ScrollTable
            label="判定履歴"
            caption="保存した判定の日時・課程・規則版・判定・総単位"
            className="check-history-table"
          >
            <thead>
              <tr>
                <th scope="col">判定日時</th>
                <th scope="col">課程</th>
                <th scope="col">規則版</th>
                <th scope="col">判定</th>
                <th scope="col">必要</th>
                <th scope="col">修得</th>
                <th scope="col">算入</th>
                <th scope="col">不足</th>
                <th scope="col">詳細</th>
              </tr>
            </thead>
            <tbody>
              {page.data.checks.map((check) => {
                const selected = check.id === selectedId;
                return (
                  <tr
                    key={check.id}
                    className={selected ? "selected" : undefined}
                    aria-current={selected ? "true" : undefined}
                  >
                    <th scope="row">
                      <time dateTime={check.createdAt}>
                        {checkedAtLabel(check.createdAt)}
                      </time>
                    </th>
                    <td>{check.curriculum.name}</td>
                    <td>{check.curriculum.revision}</td>
                    <td>
                      <span className={`judgment-label ${check.result}`}>
                        {judgmentLabels[check.result]}
                      </span>
                    </td>
                    <CreditsCell credits={check.total.requiredCredits} />
                    <CreditsCell credits={check.total.earnedCredits} />
                    <CreditsCell credits={check.total.creditedCredits} />
                    <CreditsCell credits={check.total.shortage} />
                    <td>
                      <button
                        type="button"
                        disabled={selected}
                        onClick={() => select(check.id)}
                        aria-label={`${checkedAtLabel(check.createdAt)}の判定を表示`}
                      >
                        {selected ? "表示中" : "表示"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </ScrollTable>
          <nav className="check-history-pager" aria-label="判定履歴のページ">
            <p>
              全{page.data.totalCount}件中 {page.data.offset + 1}〜
              {page.data.offset + page.data.checks.length}件
            </p>
            <button
              type="button"
              disabled={page.data.offset === 0}
              onClick={() => showPage(Math.max(0, page.data.offset - pageSize))}
            >
              新しい履歴
            </button>
            <button
              type="button"
              disabled={
                page.data.offset + page.data.checks.length >=
                page.data.totalCount
              }
              onClick={() => showPage(page.data.offset + pageSize)}
            >
              古い履歴
            </button>
          </nav>
        </>
      )}
    </section>
  );
}
