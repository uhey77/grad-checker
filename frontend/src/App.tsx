import { useCallback, useState } from "react";
import type { Application } from "./app/composition/createApplication";
import { SubjectListPage } from "./pages/subjects/SubjectListPage";
import { AppLayout } from "./layouts/AppLayout";
import { AuthGate } from "./pages/accounts/AuthGate";
import { ProfilePage } from "./pages/profiles/ProfilePage";
import { GradeEntryPage } from "./pages/grades/GradeEntryPage";
import type { ProgramOption } from "./modules/profiles/public.ts";

const screens = [
  { id: "profile", label: "所属設定" },
  { id: "grades", label: "成績入力" },
] as const;
type Screen = (typeof screens)[number]["id"];

// 画面を切り替えても未保存の入力を失わないよう、各画面は表示を切り替えるだけにする。
function StudentScreens({
  application,
  csrf,
  expire,
}: {
  application: Application;
  csrf: string;
  expire: () => void;
}) {
  const [screen, setScreen] = useState<Screen>("profile");
  // 所属と成績は同じ更新版を共有する。片方の保存をもう片方の再取得に使う。
  const [latestRevision, setLatestRevision] = useState(0);
  const reportRevision = useCallback(
    (revision: number) =>
      setLatestRevision((current) => Math.max(current, revision)),
    [],
  );
  // 成績入力の見出しを所属設定と同じ表記にするため、保存済みの所属を共有する。
  const [savedProgram, setSavedProgram] = useState<ProgramOption | null>(null);
  return (
    <>
      <main id="main-content" tabIndex={-1}>
        <nav className="screen-nav" aria-label="画面の切り替え">
          {screens.map((item) => (
            <button
              key={item.id}
              type="button"
              aria-current={screen === item.id ? "page" : undefined}
              onClick={() => setScreen(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>
        <div hidden={screen !== "profile"}>
          <ProfilePage
            useCases={application.profiles}
            csrf={csrf}
            expire={expire}
            latestRevision={latestRevision}
            reportRevision={reportRevision}
            reportProgram={setSavedProgram}
          />
        </div>
        <div hidden={screen !== "grades"}>
          <GradeEntryPage
            catalogUseCases={application.courseCatalog}
            gradeUseCases={application.grades}
            graduationUseCases={application.requirements}
            active={screen === "grades"}
            csrf={csrf}
            expire={expire}
            latestRevision={latestRevision}
            reportRevision={reportRevision}
            savedProgram={savedProgram}
            showProfile={() => setScreen("profile")}
          />
        </div>
      </main>
      <details className="subject-preview">
        <summary>科目一覧（開発用）</summary>
        <SubjectListPage useCases={application.subjects} />
      </details>
    </>
  );
}

export function App({ application }: { application: Application }) {
  return (
    <AppLayout>
      <AuthGate useCases={application.accounts}>
        {(session, expire) => (
          <StudentScreens
            key={session.student.id}
            application={application}
            csrf={session.csrfToken}
            expire={expire}
          />
        )}
      </AuthGate>
    </AppLayout>
  );
}
