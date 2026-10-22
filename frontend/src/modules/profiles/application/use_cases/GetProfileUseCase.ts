import type { ProfileRepository } from "../ports/ProfileRepository.ts";

export class GetProfileUseCase {
  constructor(private readonly repository: ProfileRepository) {}
  execute(signal?: AbortSignal) {
    return this.repository.getProfile(signal);
  }
}
