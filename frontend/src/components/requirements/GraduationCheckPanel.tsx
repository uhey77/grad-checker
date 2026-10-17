import type { GraduationResult } from "../../modules/requirements/public.ts";
import { ErrorState, LoadingState } from "../StatusPanels";
import { GraduationResultView } from "./GraduationResultView";

export function GraduationCheckPanel({
  busy,
  blocked,
  dirty,
  check,
  result,
  error,
}: {
  busy: boolean;
  blocked: boolean;
  dirty: boolean;
  check: () => void;
  result?: GraduationResult;
  error?: string;
}) {
  return (
    <section className="panel graduation-check" aria-label="卒業要件チェック">
      <h2>卒業要件チェック</h2>
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
      {busy && <LoadingState>卒業要件を判定しています…</LoadingState>}
      {error && (
        <ErrorState
          title="判定できませんでした"
          message={error}
          actionLabel="判定を再試行"
          onAction={check}
        />
      )}
      {result && <GraduationResultView result={result} />}
    </section>
  );
}
