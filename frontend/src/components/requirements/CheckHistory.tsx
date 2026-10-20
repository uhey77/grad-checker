import { useTranslation } from "react-i18next";
import type { CheckPage } from "../../modules/requirements/public.ts";
import { ScrollTable } from "../ScrollTable.tsx";
import { EmptyState, ErrorState, LoadingState } from "../StatusPanels.tsx";
import { CreditsCell } from "../subjects/SubjectCells.tsx";
import { checkedAtLabel, judgmentLabels } from "./labels.ts";
type PageState =
  | {
      status: "loading";
    }
  | {
      status: "error";
      message: string;
    }
  | {
      status: "ready";
      data: CheckPage;
    };
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
  const { t, i18n } = useTranslation();
  return (
    <section className="check-history" aria-label={t("判定履歴")}>
      <h3>{t("判定履歴")}</h3>
      {page.status === "loading" ? (
        <LoadingState>{t("判定履歴を読み込んでいます…")}</LoadingState>
      ) : page.status === "error" ? (
        <ErrorState
          title={t("判定履歴を取得できませんでした")}
          message={page.message}
          actionLabel={t("判定履歴を再取得")}
          onAction={retry}
        />
      ) : page.data.totalCount === 0 ? (
        <EmptyState
          title={t("判定履歴はまだありません")}
          message={t(
            "要件チェックを実行すると、判定結果が履歴に保存されます。",
          )}
          actionLabel={t("判定履歴を再取得")}
          onAction={retry}
        />
      ) : page.data.checks.length === 0 ? (
        <EmptyState
          title={t("このページに判定履歴はありません")}
          message={t("履歴の件数が変わった可能性があります。")}
          actionLabel={t("最新の履歴を表示")}
          onAction={() => showPage(0)}
        />
      ) : (
        <>
          <ScrollTable
            label={t("判定履歴")}
            caption={t("保存した判定の日時・課程・規則版・判定・総単位")}
            className="check-history-table"
          >
            <thead>
              <tr>
                <th scope="col">{t("判定日時")}</th>
                <th scope="col">{t("課程")}</th>
                <th scope="col">{t("規則版")}</th>
                <th scope="col">{t("判定")}</th>
                <th scope="col">{t("必要")}</th>
                <th scope="col">{t("修得")}</th>
                <th scope="col">{t("算入")}</th>
                <th scope="col">{t("不足")}</th>
                <th scope="col">{t("詳細")}</th>
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
                        {checkedAtLabel(check.createdAt, i18n.resolvedLanguage)}
                      </time>
                    </th>
                    <td>{check.curriculum.name}</td>
                    <td>{check.curriculum.revision}</td>
                    <td>
                      <span className={`judgment-label ${check.result}`}>
                        {t(judgmentLabels[check.result])}
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
                        aria-label={t("{{value0}}の判定を表示", {
                          value0: checkedAtLabel(
                            check.createdAt,
                            i18n.resolvedLanguage,
                          ),
                        })}
                      >
                        {selected ? t("表示中") : t("表示")}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </ScrollTable>
          <nav
            className="check-history-pager"
            aria-label={t("判定履歴のページ")}
          >
            <p>
              {t("全{{value0}}件中 {{value1}}〜{{value2}}件", {
                value0: page.data.totalCount,
                value1: page.data.offset + 1,
                value2: page.data.offset + page.data.checks.length,
              })}
            </p>
            <button
              type="button"
              disabled={page.data.offset === 0}
              onClick={() => showPage(Math.max(0, page.data.offset - pageSize))}
            >
              {t("新しい履歴")}
            </button>
            <button
              type="button"
              disabled={
                page.data.offset + page.data.checks.length >=
                page.data.totalCount
              }
              onClick={() => showPage(page.data.offset + pageSize)}
            >
              {t("古い履歴")}
            </button>
          </nav>
        </>
      )}
    </section>
  );
}
