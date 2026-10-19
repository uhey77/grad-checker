import type {
  CheckPage,
  CompletionAnswer,
  DashboardResult,
  GraduationResult,
  SavedCheck,
} from "../domain/models.ts";

export class GraduationError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "GraduationError";
  }
}

export interface CheckPageRequest {
  limit: number;
  offset: number;
}

export interface GraduationRepository {
  dashboard(signal?: AbortSignal): Promise<DashboardResult>;
  evaluate(signal?: AbortSignal): Promise<GraduationResult>;
  // 画面が最後に保存・取得した成績版で判定し、本人の履歴に保存する。
  createCheck(
    expectedRevision: number,
    csrf: string,
    signal?: AbortSignal,
    completionAnswers?: CompletionAnswer[],
  ): Promise<SavedCheck>;
  listChecks(page: CheckPageRequest, signal?: AbortSignal): Promise<CheckPage>;
  getCheck(id: string, signal?: AbortSignal): Promise<SavedCheck>;
}

export class GraduationUseCases implements GraduationRepository {
  constructor(private readonly repository: GraduationRepository) {}
  dashboard(signal?: AbortSignal) {
    return this.repository.dashboard(signal);
  }
  evaluate(signal?: AbortSignal) {
    return this.repository.evaluate(signal);
  }
  createCheck(
    expectedRevision: number,
    csrf: string,
    signal?: AbortSignal,
    completionAnswers?: CompletionAnswer[],
  ) {
    return this.repository.createCheck(
      expectedRevision,
      csrf,
      signal,
      completionAnswers,
    );
  }
  listChecks(page: CheckPageRequest, signal?: AbortSignal) {
    return this.repository.listChecks(page, signal);
  }
  getCheck(id: string, signal?: AbortSignal) {
    return this.repository.getCheck(id, signal);
  }
}
