import type { GetGradesUseCase } from "../use_cases/GetGradesUseCase.ts";
import type { SaveGradesUseCase } from "../use_cases/SaveGradesUseCase.ts";

// 画面へ渡す操作別UseCaseの集合。処理は持たない。
export interface GradeUseCases {
  readonly getGrades: Pick<GetGradesUseCase, "execute">;
  readonly saveGrades: Pick<SaveGradesUseCase, "execute">;
}
