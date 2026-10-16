export interface ProgramOption {
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
