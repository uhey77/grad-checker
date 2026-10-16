import {
  detailOf,
  fetchJson,
  HttpTransportError,
} from "../../../../shared/infrastructure/http.ts";
import {
  SubjectListError,
  type SubjectListErrorCode,
} from "../../application/errors/SubjectListError.ts";
import type { SubjectListRepository } from "../../application/subject-list/SubjectListRepository";
import type { SubjectListDto, ProgramDto } from "./dto";
import { toSubjectList, toProgram } from "./mappers.ts";

function codeOf(status: number): SubjectListErrorCode {
  return status === 404
    ? "not-found"
    : status === 409
      ? "conflict"
      : status >= 500
        ? "unavailable"
        : "unexpected";
}

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
      const response = await fetchJson(url, { signal });
      if (!response.ok)
        throw new SubjectListError(
          codeOf(response.status),
          detailOf(response.data),
        );
      return response.data as T;
    } catch (error) {
      if (!(error instanceof HttpTransportError)) throw error;
      throw new SubjectListError(
        error.kind === "network"
          ? "unavailable"
          : error.ok
            ? "invalid-response"
            : codeOf(error.status),
        null,
        { cause: error },
      );
    }
  }
}
