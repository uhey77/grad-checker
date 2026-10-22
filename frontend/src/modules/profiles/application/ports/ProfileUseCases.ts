import type { ListProgramsUseCase } from "../use_cases/ListProgramsUseCase.ts";
import type { GetProfileUseCase } from "../use_cases/GetProfileUseCase.ts";
import type { SaveProgramUseCase } from "../use_cases/SaveProgramUseCase.ts";

// 画面へ渡す操作別UseCaseの集合。処理は持たない。
export interface ProfileUseCases {
  readonly listPrograms: Pick<ListProgramsUseCase, "execute">;
  readonly getProfile: Pick<GetProfileUseCase, "execute">;
  readonly saveProgram: Pick<SaveProgramUseCase, "execute">;
}
