export interface Program {
  curriculumId: string;
  name: string;
  facultyName: string;
  specializationName: string | null;
  courseName: string | null;
  verificationStatus: "unverified" | "verified";
  admissionYearFrom: number | null;
  admissionYearTo: number | null;
  sourceDocument: string;
  sourcePages: string;
}

export interface Offering {
  termCode: string;
  semesterOrder: number;
  academicYear: number | null;
  sourceNote: string | null;
}

export interface Subject {
  id: string;
  code: string;
  name: string;
  credits: number;
  facultyName: string;
  departmentName: string | null;
  specializationName: string | null;
  teachingTypeLabel: string;
  subjectType: "required" | "selective" | "elective";
  classificationPath: { id: string; name: string }[];
  offerings: Offering[];
}

export interface SubjectList {
  program: Program;
  subjects: Subject[];
}
