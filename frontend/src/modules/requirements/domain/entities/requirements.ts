import type { Offering } from "../../../subjects/public.ts";
import type { CreditSummary } from "../value_objects/requirements.ts";
import type { CompletionAnswer } from "../value_objects/requirements.ts";

export interface CourseRecommendation {
  courseId: string;
  name: string;
  credits: number;
  status: "not_earned" | "pending" | "not_taken";
  isRequired: boolean;
  offerings: Offering[];
  contributions: {
    requirementId: string;
    code: string;
    name: string;
    shortageReduction: number;
    reason: string;
  }[];
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

export interface CompletionCondition extends CompletionAnswer {
  name: string;
  sourceDocument: string;
  sourcePages: string;
}
