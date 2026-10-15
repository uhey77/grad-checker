import type { Application } from "./app/composition/createApplication";
import { SubjectListPage } from "./pages/subjects/SubjectListPage";
import { AppLayout } from "./layouts/AppLayout";
import { AuthGate } from "./pages/accounts/AuthGate";

export function App({ application }: { application: Application }) {
  return (
    <AppLayout>
      <AuthGate useCases={application.accounts}>
        <SubjectListPage useCases={application.subjects} />
      </AuthGate>
    </AppLayout>
  );
}
