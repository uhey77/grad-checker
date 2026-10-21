import type { AuthRepository } from "../ports/AuthRepository.ts";

export class GetSessionUseCase {
  constructor(private readonly repository: AuthRepository) {}
  execute(signal?: AbortSignal) {
    return this.repository.session(signal);
  }
}
