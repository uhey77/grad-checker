import { Trans, useTranslation } from "react-i18next";
import { useState, type ReactNode } from "react";
import type { CompletionAnswer } from "../../../../modules/requirements/public.ts";
import type {
  CheckPage,
  SavedCheck,
} from "../../../../modules/requirements/public.ts";
import { ErrorState, LoadingState } from "../StatusPanels.tsx";
import { CheckHistory } from "./CheckHistory.tsx";
import { PastCheckView } from "./PastCheckView.tsx";
import { checkedAtLabel } from "./labels.ts";
type Remote<T> =
  | {
      status: "loading";
    }
  | {
      status: "error";
      message: string;
    }
  | ({
      status: "ready";
    } & T);
export function GraduationCheckPanel({
  busy,
  blocked,
  check,
  saved,
  error,
  history,
  children,
  completionConditions = [],
  curriculumId = "",
  degreeLevel = "bachelor",
}: {
  busy: boolean;
  blocked: boolean;
  check: (answers?: CompletionAnswer[]) => void;
  curriculumId?: string;
  degreeLevel?: "bachelor" | "master" | "doctoral";
  completionConditions?: {
    code: string;
    name: string;
  }[];
  saved?: SavedCheck;
  error?: string;
  children: ReactNode;
  history: {
    page: Remote<{
      data: CheckPage;
    }>;
    detail: Remote<{
      check: SavedCheck;
    }> | null;
    pageSize: number;
    selectedId: string | null;
    select: (id: string) => void;
    showLatest: () => void;
    showPage: (offset: number) => void;
    retryPage: () => void;
    retryDetail: () => void;
  };
}) {
  const { t, i18n } = useTranslation();
  const isGraduate = degreeLevel !== "bachelor";
  const [answerState, setAnswerState] = useState<{
    key: string;
    values: Record<string, CompletionAnswer["status"]>;
  }>({ key: curriculumId, values: {} });
  const answers = answerState.key === curriculumId ? answerState.values : {};
  function submit() {
    check(
      completionConditions.map((c) => ({
        code: c.code,
        status: answers[c.code] ?? "unknown",
      })),
    );
  }
  return (
    <section
      className="panel graduation-check"
      aria-label={t("卒業・修了要件")}
    >
      <h2>{history.detail ? t("過去の判定") : t("最新の卒業・修了要件")}</h2>
      {history.detail ? (
        <PastCheckView
          detail={history.detail}
          retry={history.retryDetail}
          showLatest={history.showLatest}
        />
      ) : (
        <>
          <p>{t("保存済みの成績を使って判定します。")}</p>
          {completionConditions.length > 0 && (
            <fieldset disabled={busy || blocked}>
              <legend>{t("単位以外の修了条件（本人申告）")}</legend>
              <p>
                {t(
                  "大学の認定状況を確認して回答してください。未入力の条件があると判定を保留します。回答はこの判定の履歴に保存されます。",
                )}
              </p>
              {completionConditions.map((c) => (
                <label key={c.code} className="completion-answer">
                  {c.name}
                  <select
                    aria-label={c.name}
                    value={answers[c.code] ?? "unknown"}
                    onChange={(e) =>
                      setAnswerState({
                        key: curriculumId,
                        values: {
                          ...answers,
                          [c.code]: e.target
                            .value as CompletionAnswer["status"],
                        },
                      })
                    }
                  >
                    <option value="unknown">{t("未確認・未入力")}</option>
                    <option value="met">{t("達成（本人申告）")}</option>
                    <option value="not_met">{t("未達成")}</option>
                  </select>
                </label>
              ))}
            </fieldset>
          )}
          <button
            type="button"
            className="primary-button"
            disabled={blocked || busy}
            onClick={submit}
          >
            {busy
              ? t("判定中…")
              : isGraduate
                ? t("修了要件をチェック")
                : t("卒業要件をチェック")}
          </button>
          <p className="check-hint">
            {t(
              "判定するたびに、結果を本人だけが見られる判定履歴に保存します。",
            )}
          </p>
          {busy && (
            <LoadingState>
              {isGraduate
                ? t("修了要件を判定しています…")
                : t("卒業要件を判定しています…")}
            </LoadingState>
          )}
          {error && (
            <ErrorState
              title={t("判定できませんでした")}
              message={error}
              actionLabel={t("判定を再試行")}
              onAction={submit}
            />
          )}
          {saved && (
            <p className="check-saved" role="status">
              <Trans
                i18nKey="最新の判定（<time>{{date}}</time>）を判定履歴に保存しました。"
                values={{
                  date: checkedAtLabel(saved.createdAt, i18n.resolvedLanguage),
                }}
                components={{ time: <time dateTime={saved.createdAt} /> }}
              />
            </p>
          )}
          {children}
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
