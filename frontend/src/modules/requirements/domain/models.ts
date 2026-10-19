export type Judgment = "pass" | "fail";

export interface CreditSummary {
  requiredCredits: number;
  earnedCredits: number;
  creditedCredits: number;
  shortage: number;
  result: Judgment;
}

export interface RequirementResult extends CreditSummary {
  id: string;
  code: string;
  name: string;
  kind:
    | "total"
    | "classification_total"
    | "required_courses"
    | "selective_group"
    | "subminimum"
    | "elective_total";
  parentId: string | null;
  classificationId: string | null;
}

export interface GraduationResult {
  result: Judgment;
  dataRevision: number;
  ruleRevisions: Record<string, number>;
  evaluatedAt: string;
  curriculum: {
    id: string;
    name: string;
    revision: number;
    sourceDocument: string;
    sourcePages: string;
  };
  total: CreditSummary;
  requirements: RequirementResult[];
  missingRequiredCourses: { courseId: string; name: string; credits: number }[];
  allocations: { requirementId: string; transferredCredits: number }[];
  externalAllocations: {
    ruleId: string;
    targetClassificationId: string;
    targetName: string;
    earnedCredits: number;
    creditedCredits: number;
    freeCredits: number;
  }[];
  warnings: "provisional_external_allocation"[];
}

export interface DashboardResult {
  result: Judgment;
  dataRevision: number;
  ruleRevisions: Record<string, number>;
  curriculumRevision: number;
  evaluatedAt: string;
  curriculum: GraduationResult["curriculum"];
  gradeCount: number;
  total: CreditSummary;
  categories: RequirementResult[];
  warnings: GraduationResult["warnings"];
}

// 保存済み判定の要約。当時の課程・規則版・総単位を保存内容から表示する。
export interface CheckSummary {
  id: string;
  createdAt: string;
  dataRevision: number;
  result: Judgment;
  curriculum: { id: string; code: string; name: string; revision: number };
  total: CreditSummary;
}

export interface CheckPage {
  checks: CheckSummary[];
  limit: number;
  offset: number;
  totalCount: number;
}

// 判定に使った1回分の成績。科目名は保存済みの判定結果から引く。
export interface CheckedGrade {
  courseId: string;
  courseName: string | null;
  attemptNo: number;
  resultStatus: "finalized" | "pending";
  gradeCode: "S" | "A" | "B" | "C" | "D" | "X" | null;
}

// 保存済みの判定。作成後は変わらず、現在の成績・マスタで再計算しない。
export interface SavedCheck {
  id: string;
  createdAt: string;
  input: {
    programId: string;
    curriculumId: string;
    dataRevision: number;
    grades: CheckedGrade[];
  };
  result: GraduationResult;
}
