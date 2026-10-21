import type { AuthRepository } from "../ports/AuthRepository.ts";

export class RecoverAccountUseCase {
  constructor(private readonly repository: AuthRepository) {}
  execute(
    loginName: string,
    recoveryCode: string,
    password: string,
    signal?: AbortSignal,
  ) {
    return this.repository.recover(loginName, recoveryCode, password, signal);
  }
}
