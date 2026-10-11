import { createSubjectsModule } from "../../modules/subjects/composition";

export function createApplication() {
  return { subjects: createSubjectsModule("/api/dev/subject-list") };
}
export type Application = ReturnType<typeof createApplication>;
