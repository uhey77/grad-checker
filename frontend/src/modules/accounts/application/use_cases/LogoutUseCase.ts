import type { AuthRepository } from "../ports/AuthRepository.ts";

export class LogoutUseCase {
  constructor(private readonly repository: AuthRepository) {}
  execute(csrf: string, signal?: AbortSignal) {
    return this.repository.logout(csrf, signal);
  }
}
