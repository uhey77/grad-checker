import { I18nextProvider, useTranslation } from "react-i18next";
import { siteI18n } from "../../i18n/setup.ts";
import { useCallback, useState } from "react";
import type { Application } from "./composition/createApplication.ts";
import { AppLayout } from "./layouts/AppLayout.tsx";
import { AuthGate, type AuthControls } from "./pages/accounts/AuthGate.tsx";
import { ProfilePage } from "./pages/profiles/ProfilePage.tsx";
import { GradeEntryPage } from "./pages/grades/GradeEntryPage.tsx";
import { HeaderNavigation } from "./components/HeaderNavigation.tsx";
import { ProfileButton } from "./components/ProfileButton.tsx";
import {
  ErrorState,
  FormError,
  LoadingState,
} from "./components/StatusPanels.tsx";
import { useProfile } from "./hooks/profiles/useProfile.ts";
import { DashboardPage } from "./pages/requirements/DashboardPage.tsx";
type Screen = "profile" | "grades" | "dashboard";
// 画面を切り替えても未保存の入力を失わないよう、各画面は表示を切り替えるだけにする。
function StudentScreens({
  application,
  csrf,
  loginName,
  expire,
  auth,
}: {
  application: Application;
  csrf: string;
  loginName: string;
  expire: () => void;
  auth: AuthControls;
}) {
  const { t } = useTranslation();
  const [screen, setScreen] = useState<Screen | null>(null);
  // 所属と成績は同じ更新版を共有する。片方の保存をもう片方の再取得に使う。
  const [latestRevision, setLatestRevision] = useState(0);
  const reportRevision = useCallback(
    (revision: number) =>
      setLatestRevision((current) => Math.max(current, revision)),
    [],
  );
  const profile = useProfile(
    application.profiles,
    csrf,
    expire,
    latestRevision,
    reportRevision,
  );
  // 最初の取得成功時だけ初期画面を決める。保存・再取得では画面を移動しない。
  if (screen === null && profile.state) {
    setScreen("dashboard");
  }
  return (
    <AppLayout
      screenKey={screen}
      navigation={
        <HeaderNavigation
          showDashboard={() => setScreen("dashboard")}
          showGrades={() => setScreen("grades")}
        />
      }
      profileAction={<ProfileButton showProfile={() => setScreen("profile")} />}
    >
      {auth.error ? (
        <div className="auth-message">
          <FormError>{auth.error}</FormError>
        </div>
      ) : null}
      {screen === null && !profile.error ? (
        <LoadingState>{t("所属情報を読み込んでいます…")}</LoadingState>
      ) : null}
      <div hidden={screen !== "dashboard"}>
        {screen !== null ? (
          !profile.state ? (
            profile.error ? (
              <ErrorState
                message={profile.error}
                actionLabel={t("再試行")}
                onAction={profile.retry}
              />
            ) : (
              <LoadingState>{t("所属情報を読み込んでいます…")}</LoadingState>
            )
          ) : (
            <DashboardPage
              useCases={application.requirements}
              active={screen === "dashboard" && !!profile.state}
              revision={latestRevision}
              curriculumId={profile.state?.profile.curriculumId ?? null}
              expire={expire}
              showProfile={() => setScreen("profile")}
            />
          )
        ) : null}
      </div>
      <div hidden={screen !== "profile" && !(screen === null && profile.error)}>
        <ProfilePage
          profile={profile}
          loginName={loginName}
          active={screen === "profile"}
          showDashboard={() => setScreen("dashboard")}
          logout={auth.logout}
          authBusy={auth.busy}
        />
      </div>
      <div hidden={screen !== "grades"}>
        {screen !== null ? (
          <GradeEntryPage
            catalogUseCases={application.courseCatalog}
            gradeUseCases={application.grades}
            csrf={csrf}
            expire={expire}
            latestRevision={latestRevision}
            reportRevision={reportRevision}
            showProfile={() => setScreen("profile")}
            showDashboard={() => setScreen("dashboard")}
          />
        ) : null}
      </div>
    </AppLayout>
  );
}
export function App({ application }: { application: Application }) {
  return (
    <I18nextProvider i18n={siteI18n}>
      <AuthGate useCases={application.accounts}>
        {(session, expire, auth) => (
          <StudentScreens
            key={session.student.id}
            application={application}
            csrf={session.csrfToken}
            loginName={session.student.loginName}
            expire={expire}
            auth={auth}
          />
        )}
      </AuthGate>
    </I18nextProvider>
  );
}
