import type { CompletionPolicy } from "../value_objects/completionPolicy.ts";

export interface ProgramOption {
  completionPolicy?: CompletionPolicy;
  programId: string;
  curriculumId: string;
  facultyName: string;
  departmentName: string | null;
  specializationName: string | null;
  courseName: string | null;
  curriculumName: string;
  revision: number;
  verificationStatus: "verified" | "unverified";
  admissionYearFrom: number | null;
  admissionYearTo: number | null;
  sourceDocument: string;
  sourcePages: string;
}
