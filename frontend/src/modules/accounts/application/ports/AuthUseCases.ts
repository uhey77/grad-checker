import type { GetAuthPolicyUseCase } from "../use_cases/GetAuthPolicyUseCase.ts";
import type { GetSessionUseCase } from "../use_cases/GetSessionUseCase.ts";
import type { RegisterAccountUseCase } from "../use_cases/RegisterAccountUseCase.ts";
import type { RecoverAccountUseCase } from "../use_cases/RecoverAccountUseCase.ts";
import type { LoginUseCase } from "../use_cases/LoginUseCase.ts";
import type { LogoutUseCase } from "../use_cases/LogoutUseCase.ts";

// 画面へ渡す操作別UseCaseの集合。処理は持たない。
export interface AuthUseCases {
  readonly config: Pick<GetAuthPolicyUseCase, "execute">;
  readonly session: Pick<GetSessionUseCase, "execute">;
  readonly register: Pick<RegisterAccountUseCase, "execute">;
  readonly recover: Pick<RecoverAccountUseCase, "execute">;
  readonly login: Pick<LoginUseCase, "execute">;
  readonly logout: Pick<LogoutUseCase, "execute">;
}
