import type { AuthRepository } from "../ports/AuthRepository.ts";

export class LoginUseCase {
  constructor(private readonly repository: AuthRepository) {}
  execute(loginName: string, password: string, signal?: AbortSignal) {
    return this.repository.login(loginName, password, signal);
  }
}
