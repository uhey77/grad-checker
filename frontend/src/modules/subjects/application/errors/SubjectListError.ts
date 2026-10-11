export type SubjectListErrorCode =
  "not-found" | "conflict" | "unavailable" | "invalid-response" | "unexpected";

export class SubjectListError extends Error {
  constructor(
    readonly code: SubjectListErrorCode,
    readonly detail: string | null = null,
    options?: ErrorOptions,
  ) {
    super(code, options);
    this.name = "SubjectListError";
  }
}
