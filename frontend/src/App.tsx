import type { Application } from "./app/composition/createApplication";
import { SubjectListPage } from "./pages/subjects/SubjectListPage";
import { AppLayout } from "./layouts/AppLayout";

export function App({ application }: { application: Application }) {
  return (
    <AppLayout>
      <SubjectListPage useCases={application.subjects} />
    </AppLayout>
  );
}
