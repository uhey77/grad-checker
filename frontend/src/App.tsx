import { useCallback, useEffect, useRef, useState } from "react";
import type { Application } from "./app/composition/createApplication";
import { SubjectListPage } from "./pages/subjects/SubjectListPage";
import { AppLayout } from "./layouts/AppLayout";
import { AuthGate, type AuthControls } from "./pages/accounts/AuthGate";
import { ProfilePage } from "./pages/profiles/ProfilePage";
import { GradeEntryPage } from "./pages/grades/GradeEntryPage";
import { UserMenu } from "./components/accounts/UserMenu";
import { FormError, LoadingState } from "./components/StatusPanels";
import { useProfile } from "./hooks/profiles/useProfile";

type Screen = "profile" | "grades";

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
  const [screen, setScreen] = useState<Screen | null>(null);
  const main = useRef<HTMLElement>(null);
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
    setScreen(profile.state.profile.curriculumId ? "grades" : "profile");
  }
  useEffect(() => {
    if (screen) main.current?.focus();
  }, [screen]);
  return (
    <AppLayout
      userMenu={
        <UserMenu
          loginName={loginName}
          busy={auth.busy}
          showProfile={() => setScreen("profile")}
          logout={auth.logout}
        />
      }
    >
      {auth.error ? (
        <div className="auth-message">
          <FormError>{auth.error}</FormError>
        </div>
      ) : null}
      <main id="main-content" tabIndex={-1} ref={main}>
        {screen === null && !profile.error ? (
          <LoadingState>所属情報を読み込んでいます…</LoadingState>
        ) : null}
        <div
          hidden={screen !== "profile" && !(screen === null && profile.error)}
        >
          <ProfilePage
            profile={profile}
            loginName={loginName}
            active={screen === "profile"}
            showGrades={() => setScreen("grades")}
          />
        </div>
        <div hidden={screen !== "grades"}>
          {screen !== null ? (
            <GradeEntryPage
              catalogUseCases={application.courseCatalog}
              gradeUseCases={application.grades}
              graduationUseCases={application.requirements}
              active={screen === "grades"}
              csrf={csrf}
              expire={expire}
              latestRevision={latestRevision}
              reportRevision={reportRevision}
              savedProgram={profile.savedProgram ?? null}
              showProfile={() => setScreen("profile")}
            />
          ) : null}
        </div>
      </main>
      <details className="subject-preview">
        <summary>科目一覧（開発用）</summary>
        <SubjectListPage useCases={application.subjects} />
      </details>
    </AppLayout>
  );
}

export function App({ application }: { application: Application }) {
  return (
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
  );
}
