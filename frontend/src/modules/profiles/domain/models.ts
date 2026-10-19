export interface CompletionPolicy {
  degreeLevel: "bachelor" | "master" | "doctoral";
  campus: "hachioji" | "kamata";
  catalogStatus: "verified" | "unverified";
  requirementsStatus: "verified" | "unverified";
  rulesStatus: "verified" | "unverified";
  unresolvedReasons: string[];
  sourceDocument: string;
  sourcePages: string;
  conditions: {
    code: string;
    name: string;
    sourceDocument: string;
    sourcePages: string;
  }[];
}

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

export interface Profile {
  studentId: string;
  loginName: string;
  programId: string | null;
  curriculumId: string | null;
  dataRevision: number;
}

export interface ProgramSelection {
  programId: string;
  curriculumId: string;
  expectedRevision: number;
}
