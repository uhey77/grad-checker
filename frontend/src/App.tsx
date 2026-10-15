import type { Application } from "./app/composition/createApplication";
import { SubjectListPage } from "./pages/subjects/SubjectListPage";
import { AppLayout } from "./layouts/AppLayout";
import { AuthGate } from "./pages/accounts/AuthGate";

export function App({
  application,
  verificationToken = "",
}: {
  application: Application;
  verificationToken?: string;
}) {
  return (
    <AppLayout>
      <AuthGate
        useCases={application.accounts}
        verificationToken={verificationToken}
      >
        <SubjectListPage useCases={application.subjects} />
      </AuthGate>
    </AppLayout>
  );
}
