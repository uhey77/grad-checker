import {
  requestJson,
  type JsonRequest,
} from "../../../shared/infrastructure/http.ts";
import {
  GraduationError,
  type CheckPageRequest,
  type GraduationRepository,
} from "../application/GraduationUseCases.ts";
import { toCheckPage, toGraduationResult, toSavedCheck } from "./mappers.ts";

export class HttpGraduationRepository implements GraduationRepository {
  constructor(private readonly base: string) {}
  async evaluate(signal?: AbortSignal) {
    const data = await requestJson(
      this.base + "/me/graduation-requirements",
      { signal },
      (status, message) => new GraduationError(status, message),
      {
        unreadable: "卒業要件の判定結果を読み込めません。",
        failed: "卒業要件を判定できませんでした。",
      },
    );
    return toGraduationResult(data);
  }
  private checks(path: string, request: JsonRequest, failed: string) {
    return requestJson(
      this.base + "/checks" + path,
      request,
      (status, message) => new GraduationError(status, message),
      { unreadable: "判定履歴を読み込めません。", failed },
    );
  }
  async createCheck(
    expectedRevision: number,
    csrf: string,
    signal?: AbortSignal,
  ) {
    const check = toSavedCheck(
      await this.checks(
        "",
        {
          method: "POST",
          payload: { expected_revision: expectedRevision },
          csrf,
          signal,
        },
        "卒業要件を判定・保存できませんでした。",
      ),
    );
    // 保存した履歴は要求した成績版で判定したものに限る。
    if (check.input.dataRevision !== expectedRevision)
      throw new GraduationError(502, "判定履歴を読み込めません。");
    return check;
  }
  async listChecks(page: CheckPageRequest, signal?: AbortSignal) {
    const query = new URLSearchParams({
      limit: String(page.limit),
      offset: String(page.offset),
    });
    const result = toCheckPage(
      await this.checks(
        "?" + query.toString(),
        { signal },
        "判定履歴を取得できませんでした。",
      ),
    );
    if (result.limit !== page.limit || result.offset !== page.offset)
      throw new GraduationError(502, "判定履歴を読み込めません。");
    return result;
  }
  async getCheck(id: string, signal?: AbortSignal) {
    const check = toSavedCheck(
      await this.checks(
        "/" + encodeURIComponent(id),
        { signal },
        "判定履歴を取得できませんでした。",
      ),
    );
    if (check.id !== id)
      throw new GraduationError(502, "判定履歴を読み込めません。");
    return check;
  }
}
