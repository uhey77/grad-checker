import { useTranslation } from "react-i18next";
import type { GraduationUseCases } from "../../../../modules/requirements/public.ts";
import type { ProgramOption } from "../../../../modules/profiles/public.ts";
import { useDashboard } from "../../hooks/requirements/useDashboard.ts";
import { useDashboardDetail } from "../../hooks/requirements/useDashboardDetail.ts";
import { PageHeading } from "../../components/PageHeading.tsx";
import { ErrorState, LoadingState } from "../../components/StatusPanels.tsx";
import { programLabel } from "../../components/subjects/labels.ts";
import { GraduationOverview } from "../../components/requirements/GraduationOverview.tsx";
import { GraduationResultView } from "../../components/requirements/GraduationResultView.tsx";
import { GraduationCheckPanel } from "../../components/requirements/GraduationCheckPanel.tsx";
import { useCheckHistory } from "../../hooks/requirements/useCheckHistory.ts";
import { useGraduationCheck } from "../../hooks/requirements/useGraduationCheck.ts";
export function DashboardPage({
  useCases,
  csrf,
  active,
  revision,
  curriculumId,
  savedProgram,
  expire,
  showProfile,
  showGrades,
}: {
  useCases: GraduationUseCases;
  csrf: string;
  active: boolean;
  revision: number;
  curriculumId: string | null;
  savedProgram: ProgramOption | null;
  expire: () => void;
  showProfile: () => void;
  showGrades: () => void;
}) {
  const { t } = useTranslation();
  const dashboard = useDashboard(
    useCases,
    active,
    revision,
    curriculumId,
    expire,
  );
  const summary = dashboard.summary;
  const result = summary.status === "ready" ? summary.data : null;
  const history = useCheckHistory(useCases, active && !!curriculumId, expire);
  const check = useGraduationCheck(
    useCases,
    result?.dataRevision ?? revision,
    curriculumId ?? "",
    csrf,
    active,
    !result,
    expire,
    () => {
      history.showLatest();
      history.refresh();
    },
  );
  const completionPolicy =
    savedProgram?.curriculumId === curriculumId
      ? savedProgram.completionPolicy
      : undefined;
  const detail = useDashboardDetail(
    useCases,
    result,
    active && dashboard.expanded && !check.saved && !history.detail,
    expire,
  );
  const displayedResult = check.saved?.result ?? result;
  const categories = check.saved
    ? check.saved.result.requirements.filter(
        (row) => row.kind === "classification_total",
      )
    : (result?.categories ?? []);
  const displayedDetail =
    check.saved?.result ?? (detail.status === "ready" ? detail.data : null);
  function refresh() {
    check.reset();
    dashboard.retry();
  }
  return (
    <div className="dashboard-page">
      <PageHeading title={t("ダッシュボード")} />
      <section className="panel dashboard-context" aria-label={t("所属と操作")}>
        <h2>{t("所属")}</h2>
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
      ) : (
        <GraduationCheckPanel
          busy={check.busy}
          blocked={!result}
          check={(answers) => void check.check(answers)}
          curriculumId={curriculumId}
          degreeLevel={completionPolicy?.degreeLevel}
          completionConditions={completionPolicy?.conditions}
          saved={check.saved}
          error={check.error}
          history={history}
          refresh={refresh}
        >
          {summary.status === "error" ? (
            <ErrorState
              title={t("概要を取得できませんでした")}
              message={dashboard.message(summary.error)}
              actionLabel={t("再試行")}
              onAction={refresh}
            />
          ) : !displayedResult ? (
            <LoadingState>
              {t("卒業・修了要件の概要を読み込んでいます…")}
            </LoadingState>
          ) : (
            <>
              {result?.gradeCount === 0 && (
                <p role="status">
                  {t(
                    "保存済みの成績は0件です。成績入力から修得状況を保存してください。",
                  )}
                </p>
              )}
              <GraduationOverview
                key={displayedResult.evaluatedAt}
                result={displayedResult}
                categories={categories}
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
                  {displayedDetail ? (
                    <GraduationResultView
                      result={displayedDetail}
                      showOverview={false}
                    />
                  ) : detail.status === "error" ? (
                    <ErrorState
                      message={dashboard.message(detail.error)}
                      actionLabel={t("概要から再取得")}
                      onAction={refresh}
                    />
                  ) : (
                    <LoadingState>
                      {t("卒業要件の詳細を読み込んでいます…")}
                    </LoadingState>
                  )}
                </div>
              )}
            </>
          )}
        </GraduationCheckPanel>
      )}
    </div>
  );
}
