import {
  requestJson,
  type JsonRequest,
} from "../../../../shared/infrastructure/http.ts";
import { GradeError } from "../../application/errors/GradeError.ts";
import { type GradeRepository } from "../../application/ports/GradeRepository.ts";
import type { GradeSet } from "../../application/dto/grades.ts";
import { toGradeSetDto, toStudentGrades } from "./schemas/mappers.ts";

export class HttpGradeRepository implements GradeRepository {
  constructor(private readonly base: string) {}
  private request(request: JsonRequest): Promise<unknown> {
    return requestJson(
      this.base + "/me/grades",
      request,
      (status, message) => new GradeError(status, message),
      {
        unreadable: "成績サービスの応答を読み込めません。",
        failed: "成績の処理に失敗しました。",
      },
    );
  }
  async getGrades(signal?: AbortSignal) {
    return toStudentGrades(await this.request({ signal }));
  }
  async saveGrades(gradeSet: GradeSet, csrf: string, signal?: AbortSignal) {
    return toStudentGrades(
      await this.request({
        method: "PUT",
        payload: toGradeSetDto(gradeSet),
        csrf,
        signal,
      }),
    );
  }
}
