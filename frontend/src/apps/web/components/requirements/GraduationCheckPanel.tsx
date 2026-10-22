import { Trans, useTranslation } from "react-i18next";
import { useState } from "react";
import type { CompletionAnswer } from "../../../../modules/requirements/public.ts";
import type {
  CheckPage,
  SavedCheck,
} from "../../../../modules/requirements/public.ts";
import { ErrorState, LoadingState } from "../StatusPanels.tsx";
import { CheckHistory } from "./CheckHistory.tsx";
import { GraduationResultView } from "./GraduationResultView.tsx";
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
  dirty,
  check,
  saved,
  error,
  history,
  completionConditions = [],
  curriculumId = "",
  degreeLevel = "bachelor",
}: {
  busy: boolean;
  blocked: boolean;
  dirty: boolean;
  check: (answers?: CompletionAnswer[]) => void;
  curriculumId?: string;
  degreeLevel?: "bachelor" | "master" | "doctoral";
  completionConditions?: {
    code: string;
    name: string;
  }[];
  saved?: SavedCheck;
  error?: string;
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
      aria-label={isGraduate ? t("修了要件チェック") : t("卒業要件チェック")}
    >
      <h2>{isGraduate ? t("修了要件チェック") : t("卒業要件チェック")}</h2>
      {history.detail ? (
        <PastCheckView
          detail={history.detail}
          retry={history.retryDetail}
          showLatest={history.showLatest}
        />
      ) : (
        <>
          {dirty && (
            <p>
              {t(
                "未保存の変更があります。成績を保存してから判定してください。",
              )}
            </p>
          )}
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
            <>
              <p className="check-saved" role="status">
                <Trans
                  i18nKey="最新の判定（<time>{{date}}</time>）を判定履歴に保存しました。"
                  values={{
                    date: checkedAtLabel(
                      saved.createdAt,
                      i18n.resolvedLanguage,
                    ),
                  }}
                  components={{ time: <time dateTime={saved.createdAt} /> }}
                />
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
