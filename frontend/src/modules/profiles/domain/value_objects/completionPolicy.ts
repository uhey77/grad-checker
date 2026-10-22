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
