import type { AuthRepository } from "../ports/AuthRepository.ts";

export class GetAuthPolicyUseCase {
  constructor(private readonly repository: AuthRepository) {}
  execute(signal?: AbortSignal) {
    return this.repository.config(signal);
  }
}
