import { GetAuthPolicyUseCase } from "./application/use_cases/GetAuthPolicyUseCase.ts";
import { GetSessionUseCase } from "./application/use_cases/GetSessionUseCase.ts";
import { RegisterAccountUseCase } from "./application/use_cases/RegisterAccountUseCase.ts";
import { RecoverAccountUseCase } from "./application/use_cases/RecoverAccountUseCase.ts";
import { LoginUseCase } from "./application/use_cases/LoginUseCase.ts";
import { LogoutUseCase } from "./application/use_cases/LogoutUseCase.ts";
import type { AuthUseCases } from "./application/ports/AuthUseCases.ts";
import { HttpAuthRepository } from "./infrastructure/HttpAuthRepository.ts";

export function createAccountsModule(base: string): AuthUseCases {
  const repository = new HttpAuthRepository(base);
  return {
    config: new GetAuthPolicyUseCase(repository),
    session: new GetSessionUseCase(repository),
    register: new RegisterAccountUseCase(repository),
    recover: new RecoverAccountUseCase(repository),
    login: new LoginUseCase(repository),
    logout: new LogoutUseCase(repository),
  };
}
