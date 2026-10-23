import { useTranslation } from "react-i18next";
import type { GraduationUseCases } from "../../../../modules/requirements/public.ts";
import { useDashboard } from "../../hooks/requirements/useDashboard.ts";
import { useDashboardDetail } from "../../hooks/requirements/useDashboardDetail.ts";
import { PageHeading } from "../../components/PageHeading.tsx";
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "../../components/StatusPanels.tsx";
import { GraduationOverview } from "../../components/requirements/GraduationOverview.tsx";
import { GraduationResultView } from "../../components/requirements/GraduationResultView.tsx";
export function DashboardPage({
  useCases,
  active,
  revision,
  curriculumId,
  expire,
  showProfile,
}: {
  useCases: GraduationUseCases;
  active: boolean;
  revision: number;
  curriculumId: string | null;
  expire: () => void;
  showProfile: () => void;
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
  const detail = useDashboardDetail(
    useCases,
    result,
    active && dashboard.expanded,
    expire,
  );
  const displayedDetail = detail.status === "ready" ? detail.data : null;
  return (
    <div className="dashboard-page">
      <PageHeading title={t("ダッシュボード")} />
      {!curriculumId ? (
        <EmptyState
          title={t("所属は未設定です。")}
          message={t(
            "マイページで所属を保存すると、卒業・修了要件の概要を確認できます。",
          )}
          actionLabel={t("所属を設定")}
          onAction={showProfile}
        />
      ) : (
        <section
          className="panel requirements-panel"
          aria-label={t("卒業・修了要件")}
        >
          {summary.status === "error" ? (
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
            <>
              {result?.gradeCount === 0 && (
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
                  {displayedDetail ? (
                    <GraduationResultView
                      result={displayedDetail}
                      showOverview={false}
                    />
                  ) : detail.status === "error" ? (
                    <ErrorState
                      message={dashboard.message(detail.error)}
                      actionLabel={t("再試行")}
                      onAction={dashboard.retry}
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
        </section>
      )}
    </div>
  );
}
