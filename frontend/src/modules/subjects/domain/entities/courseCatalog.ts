import type { Offering } from "../value_objects/offering.ts";
import type { CoursePlacement } from "../value_objects/course.ts";

export interface CatalogCurriculum {
  curriculumId: string;
  name: string;
  verificationStatus: "verified" | "unverified";
  admissionYearFrom: number | null;
  admissionYearTo: number | null;
  sourceDocument: string;
  sourcePages: string;
}

export interface CatalogCategory {
  id: string;
  code: string;
  name: string;
  parentId: string | null;
  level: number;
  displayOrder: number;
}

export interface CatalogCourse {
  courseId: string;
  code: string;
  name: string;
  credits: number;
  offeringFacultyName: string;
  offeringDepartmentName: string | null;
  offeringSpecializationName: string | null;
  teachingTypeLabel: string;
  offerings: Offering[];
  placement: CoursePlacement | null;
}
