import { createSubjectsModule } from "../../modules/subjects/composition";
import { createAccountsModule } from "../../modules/accounts/composition";

export function createApplication() {
  return {
    subjects: createSubjectsModule("/api/dev/subject-list"),
    accounts: createAccountsModule("/api/auth"),
  };
}
export type Application = ReturnType<typeof createApplication>;
