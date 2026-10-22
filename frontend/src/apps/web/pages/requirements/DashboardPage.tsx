import { Trans, useTranslation } from "react-i18next";
import type { GraduationUseCases } from "../../../../modules/requirements/public.ts";
import type { ProgramOption } from "../../../../modules/profiles/public.ts";
import { useDashboard } from "../../hooks/requirements/useDashboard.ts";
import { PageHeading } from "../../components/PageHeading.tsx";
import { ErrorState, LoadingState } from "../../components/StatusPanels.tsx";
import { programLabel } from "../../components/subjects/labels.ts";
import { GraduationOverview } from "../../components/requirements/GraduationOverview.tsx";
import { GraduationResultView } from "../../components/requirements/GraduationResultView.tsx";
import { checkedAtLabel } from "../../components/requirements/labels.ts";
export function DashboardPage({
  useCases,
  active,
  revision,
  curriculumId,
  savedProgram,
  expire,
  showProfile,
  showGrades,
}: {
  useCases: GraduationUseCases;
  active: boolean;
  revision: number;
  curriculumId: string | null;
  savedProgram: ProgramOption | null;
  expire: () => void;
  showProfile: () => void;
  showGrades: () => void;
}) {
  const { t, i18n } = useTranslation();
  const dashboard = useDashboard(
    useCases,
    active,
    revision,
    curriculumId,
    expire,
  );
  const summary = dashboard.summary;
  const result = summary.status === "ready" ? summary.data : null;
  return (
    <div className="dashboard-page">
      <PageHeading title={t("ダッシュボード")} />
      <section className="panel dashboard-context" aria-label={t("所属と操作")}>
        <h2>{t("本人の所属")}</h2>
        <p>
          {savedProgram
            ? programLabel(savedProgram)
            : curriculumId
              ? t("選択肢にないカリキュラム")
              : t("所属は未設定です。")}
        </p>
        <div className="dashboard-actions">
          <button type="button" onClick={showProfile}>
            {curriculumId ? t("所属を確認・変更") : t("所属を設定")}
          </button>
          <button
            type="button"
            className="primary-button"
            disabled={!curriculumId}
            onClick={showGrades}
          >
            {t("成績入力へ進む")}
          </button>
        </div>
      </section>
      {!curriculumId ? (
        <p role="status">
          {t(
            "マイページで所属を保存すると、卒業・修了要件の概要を確認できます。",
          )}
        </p>
      ) : summary.status === "error" ? (
        <ErrorState
          title={t("概要を取得できませんでした")}
          message={dashboard.message(summary.error)}
          actionLabel={t("再試行")}
          onAction={dashboard.retry}
        />
      ) : !result ? (
        <LoadingState>
          {t("卒業・修了要件の概要を読み込んでいます…")}
        </LoadingState>
      ) : (
        <section
          className="panel graduation-check"
          aria-label={t("最新の卒業・修了要件概要")}
        >
          <div className="dashboard-actions">
            <h2>{t("最新の卒業・修了要件")}</h2>
            <button type="button" onClick={dashboard.retry}>
              {t("概要を再取得")}
            </button>
          </div>
          <p>
            {t(
              "保存済みの成績に基づく単位要件の確認です。大学による正式な卒業・修了認定ではありません。",
            )}
          </p>
          <p>
            <Trans
              i18nKey="未保存の入力は反映されません。<time>{{date}}</time> 時点"
              values={{
                date: checkedAtLabel(result.evaluatedAt, i18n.resolvedLanguage),
              }}
              components={{ time: <time dateTime={result.evaluatedAt} /> }}
            />
          </p>
          {result.gradeCount === 0 && (
            <p role="status">
              {t(
                "保存済みの成績は0件です。成績入力から修得状況を保存してください。",
              )}
            </p>
          )}
          <GraduationOverview
            key={result.evaluatedAt}
            result={result}
            categories={result.categories}
          />
          <button
            type="button"
            aria-expanded={dashboard.expanded}
            aria-controls="dashboard-detail"
            onClick={dashboard.toggleDetail}
          >
            {dashboard.expanded
              ? t("条件別の詳細を閉じる")
              : t("条件別の詳細を表示")}
          </button>
          {dashboard.expanded && (
            <div id="dashboard-detail">
              {dashboard.detail.status === "error" ? (
                <ErrorState
                  message={dashboard.message(dashboard.detail.error)}
                  actionLabel={t("概要から再取得")}
                  onAction={dashboard.retry}
                />
              ) : dashboard.detail.status === "ready" ? (
                <GraduationResultView
                  result={dashboard.detail.data}
                  showOverview={false}
                />
              ) : (
                <LoadingState>
                  {t("卒業要件の詳細を読み込んでいます…")}
                </LoadingState>
              )}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
