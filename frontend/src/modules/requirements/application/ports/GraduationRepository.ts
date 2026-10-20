import type {
  CheckPage,
  CompletionAnswer,
  DashboardResult,
  GraduationResult,
  SavedCheck,
} from "../../domain/models.ts";
import type { CheckPageRequest } from "../dto/CheckPageRequest.ts";
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
