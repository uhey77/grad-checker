import {
  GradeError,
  type GradeRepository,
} from "../application/GradeUseCases.ts";
import type { GradeSet } from "../domain/models.ts";
import { toGradeSetDto, toStudentGrades } from "./mappers.ts";

export class HttpGradeRepository implements GradeRepository {
  constructor(private readonly base: string) {}
  private async request(
    signal?: AbortSignal,
    payload?: object,
    csrf?: string,
  ): Promise<unknown> {
    try {
      const response = await fetch(this.base + "/me/grades", {
        method: payload ? "PUT" : "GET",
        credentials: "same-origin",
        cache: "no-store",
        signal,
        headers: payload
          ? { "Content-Type": "application/json", "X-CSRF-Token": csrf ?? "" }
          : undefined,
        body: payload ? JSON.stringify(payload) : undefined,
      });
      let data: unknown;
      try {
        data = await response.json();
      } catch {
        if (signal?.aborted) throw signal.reason;
        throw new GradeError(
          response.ok ? 502 : response.status,
          "成績サービスの応答を読み込めません。",
        );
      }
      if (!response.ok) {
        const detail =
          data &&
          typeof data === "object" &&
          "detail" in data &&
          typeof data.detail === "string"
            ? data.detail
            : "成績の処理に失敗しました。";
        throw new GradeError(response.status, detail);
      }
      return data;
    } catch (error) {
      if (signal?.aborted || error instanceof GradeError) throw error;
      throw new GradeError(
        0,
        "サーバーへ接続できません。時間をおいて再試行してください。",
      );
    }
  }
  async getGrades(signal?: AbortSignal) {
    return toStudentGrades(await this.request(signal));
  }
  async saveGrades(gradeSet: GradeSet, csrf: string, signal?: AbortSignal) {
    return toStudentGrades(
      await this.request(signal, toGradeSetDto(gradeSet), csrf),
    );
  }
}
