import type { Application } from "./app/composition/createApplication";
import { SubjectListPage } from "./pages/subjects/SubjectListPage";
import { AppLayout } from "./layouts/AppLayout";
import { AuthGate } from "./pages/accounts/AuthGate";
import { ProfilePage } from "./pages/profiles/ProfilePage";

export function App({ application }: { application: Application }) {
  return (
    <AppLayout>
      <AuthGate useCases={application.accounts}>
        {(session, expire) => (
          <div key={session.student.id}>
            <ProfilePage
              useCases={application.profiles}
              csrf={session.csrfToken}
              expire={expire}
            />
            <details className="subject-preview">
              <summary>科目一覧（開発用）</summary>
              <SubjectListPage useCases={application.subjects} />
            </details>
          </div>
        )}
      </AuthGate>
    </AppLayout>
  );
}
