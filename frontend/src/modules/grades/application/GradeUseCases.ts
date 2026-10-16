import type { GradeSet, StudentGrades } from "../domain/models.ts";

// 成績の取得・保存の失敗。statusは外部APIのHTTPステータス（通信失敗は0）。
export class GradeError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "GradeError";
  }
}

export interface GradeRepository {
  getGrades(signal?: AbortSignal): Promise<StudentGrades>;
  saveGrades(
    gradeSet: GradeSet,
    csrf: string,
    signal?: AbortSignal,
  ): Promise<StudentGrades>;
}

export class GradeUseCases implements GradeRepository {
  constructor(private readonly repository: GradeRepository) {}
  getGrades(signal?: AbortSignal) {
    return this.repository.getGrades(signal);
  }
  // 省略した回次は取消になるため、表示中の絞り込み結果ではなく全集合を送る。
  saveGrades(gradeSet: GradeSet, csrf: string, signal?: AbortSignal) {
    return this.repository.saveGrades(gradeSet, csrf, signal);
  }
}
