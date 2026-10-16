import {
  createCourseCatalogModule,
  createSubjectsModule,
} from "../../modules/subjects/composition";
import { createGradesModule } from "../../modules/grades/composition";
import { createAccountsModule } from "../../modules/accounts/composition";
import { createProfilesModule } from "../../modules/profiles/composition";

export function createApplication() {
  return {
    subjects: createSubjectsModule("/api/dev/subject-list"),
    accounts: createAccountsModule("/api/auth"),
    profiles: createProfilesModule("/api"),
    courseCatalog: createCourseCatalogModule("/api"),
    grades: createGradesModule("/api"),
  };
}
export type Application = ReturnType<typeof createApplication>;
