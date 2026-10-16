import type { Offering } from "../subject-list/models.ts";

export type CourseType = "required" | "selective" | "elective";

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

// 本人課程の科目表にある科目だけが持つ分類・種別。課程外の科目には推測で設定しない。
export interface CoursePlacement {
  classificationPath: { id: string; name: string }[];
  courseType: CourseType;
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

export interface CourseCatalog {
  curriculum: CatalogCurriculum;
  categories: CatalogCategory[];
  courses: CatalogCourse[];
}
