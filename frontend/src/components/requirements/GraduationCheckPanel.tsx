import type {
  CheckPage,
  SavedCheck,
} from "../../modules/requirements/public.ts";
import { ErrorState, LoadingState } from "../StatusPanels";
import { CheckHistory } from "./CheckHistory";
import { GraduationResultView } from "./GraduationResultView";
import { PastCheckView } from "./PastCheckView";
import { checkedAtLabel } from "./labels";

type Remote<T> =
  | { status: "loading" }
  | { status: "error"; message: string }
  | ({ status: "ready" } & T);

export function GraduationCheckPanel({
  busy,
  blocked,
  dirty,
  check,
  saved,
  error,
  history,
}: {
  busy: boolean;
  blocked: boolean;
  dirty: boolean;
  check: () => void;
  saved?: SavedCheck;
  error?: string;
  history: {
    page: Remote<{ data: CheckPage }>;
    detail: Remote<{ check: SavedCheck }> | null;
    pageSize: number;
    selectedId: string | null;
    select: (id: string) => void;
    showLatest: () => void;
    showPage: (offset: number) => void;
    retryPage: () => void;
    retryDetail: () => void;
  };
}) {
  return (
    <section className="panel graduation-check" aria-label="卒業要件チェック">
      <h2>卒業要件チェック</h2>
      {history.detail ? (
        <PastCheckView
          detail={history.detail}
          retry={history.retryDetail}
          showLatest={history.showLatest}
        />
      ) : (
        <>
          {dirty && (
            <p>未保存の変更があります。成績を保存してから判定してください。</p>
          )}
          <button
            type="button"
            className="primary-button"
            disabled={blocked || busy}
            onClick={check}
          >
            {busy ? "判定中…" : "卒業要件をチェック"}
          </button>
          <p className="check-hint">
            判定するたびに、結果を本人だけが見られる判定履歴に保存します。
          </p>
          {busy && <LoadingState>卒業要件を判定しています…</LoadingState>}
          {error && (
            <ErrorState
              title="判定できませんでした"
              message={error}
              actionLabel="判定を再試行"
              onAction={check}
            />
          )}
          {saved && (
            <>
              <p className="check-saved" role="status">
                最新の判定（
                <time dateTime={saved.createdAt}>
                  {checkedAtLabel(saved.createdAt)}
                </time>
                ）を判定履歴に保存しました。
              </p>
              <GraduationResultView result={saved.result} />
            </>
          )}
        </>
      )}
      <CheckHistory
        page={history.page}
        pageSize={history.pageSize}
        selectedId={history.selectedId}
        select={history.select}
        showPage={history.showPage}
        retry={history.retryPage}
      />
    </section>
  );
}
