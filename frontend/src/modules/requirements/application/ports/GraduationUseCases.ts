import type { GetDashboardUseCase } from "../use_cases/GetDashboardUseCase.ts";
import type { EvaluateGraduationUseCase } from "../use_cases/EvaluateGraduationUseCase.ts";
import type { CreateCheckUseCase } from "../use_cases/CreateCheckUseCase.ts";
import type { ListChecksUseCase } from "../use_cases/ListChecksUseCase.ts";
import type { GetCheckUseCase } from "../use_cases/GetCheckUseCase.ts";

// 画面へ渡す操作別UseCaseの集合。処理は持たない。
export interface GraduationUseCases {
  readonly dashboard: Pick<GetDashboardUseCase, "execute">;
  readonly evaluate: Pick<EvaluateGraduationUseCase, "execute">;
  readonly createCheck: Pick<CreateCheckUseCase, "execute">;
  readonly listChecks: Pick<ListChecksUseCase, "execute">;
  readonly getCheck: Pick<GetCheckUseCase, "execute">;
}
