import { requestJson } from "../../../shared/infrastructure/http.ts";
import {
  GraduationError,
  type GraduationRepository,
} from "../application/GraduationUseCases.ts";
import { toGraduationResult } from "./mappers.ts";

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
}
