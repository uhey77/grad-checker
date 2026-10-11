import { SubjectListError } from "../../application/errors/SubjectListError.ts";
import type { SubjectListRepository } from "../../application/subject-list/SubjectListRepository";
import type { SubjectListDto, ProgramDto } from "./dto";
import { toSubjectList, toProgram } from "./mappers.ts";

export class HttpSubjectListRepository implements SubjectListRepository {
  constructor(private readonly baseUrl: string) {}

  async listPrograms(signal: AbortSignal) {
    const body = await this.request<ProgramDto[]>(
      `${this.baseUrl}/programs`,
      signal,
    );
    return body.map(toProgram);
  }

  async getSubjectList(curriculumId: string, signal: AbortSignal) {
    const body = await this.request<SubjectListDto>(
      `${this.baseUrl}/${encodeURIComponent(curriculumId)}`,
      signal,
    );
    return toSubjectList(body);
  }

  private async request<T>(url: string, signal: AbortSignal): Promise<T> {
    try {
      const response = await fetch(url, { signal });
      const body: unknown = await response.json();
      if (!response.ok) {
        const detail =
          typeof body === "object" && body !== null && "detail" in body
            ? body.detail
            : null;
        throw new SubjectListError(
          response.status === 404
            ? "not-found"
            : response.status === 409
              ? "conflict"
              : response.status >= 500
                ? "unavailable"
                : "unexpected",
          typeof detail === "string" ? detail : null,
        );
      }
      return body as T;
    } catch (error) {
      if (error instanceof TypeError || error instanceof SyntaxError)
        throw new SubjectListError(
          error instanceof SyntaxError ? "invalid-response" : "unavailable",
          null,
          { cause: error },
        );
      throw error;
    }
  }
}
