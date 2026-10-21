export type Judgment = "pass" | "fail" | "pending";

export interface CreditSummary {
  requiredCredits: number;
  earnedCredits: number;
  creditedCredits: number;
  shortage: number;
  result: "pass" | "fail";
}

export interface CompletionAnswer {
  code: string;
  status: "met" | "not_met" | "unknown";
}
