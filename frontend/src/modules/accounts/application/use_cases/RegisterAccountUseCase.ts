import type { AuthRepository } from "../ports/AuthRepository.ts";

export class RegisterAccountUseCase {
  constructor(private readonly repository: AuthRepository) {}
  execute(loginName: string, password: string, signal?: AbortSignal) {
    return this.repository.register(loginName, password, signal);
  }
}
