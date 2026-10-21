import {
  createCourseCatalogModule,
  createSubjectsModule,
} from "../../../modules/subjects/composition.ts";
import { createGradesModule } from "../../../modules/grades/composition.ts";
import { createAccountsModule } from "../../../modules/accounts/composition.ts";
import { createProfilesModule } from "../../../modules/profiles/composition.ts";
import { createRequirementsModule } from "../../../modules/requirements/composition.ts";

export function createApplication() {
  return {
    subjects: createSubjectsModule("/api/dev/subject-list"),
    accounts: createAccountsModule("/api/auth"),
    profiles: createProfilesModule("/api"),
    courseCatalog: createCourseCatalogModule("/api"),
    grades: createGradesModule("/api"),
    requirements: createRequirementsModule("/api"),
  };
}
export type Application = ReturnType<typeof createApplication>;
