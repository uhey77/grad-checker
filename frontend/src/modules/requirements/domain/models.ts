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
}
