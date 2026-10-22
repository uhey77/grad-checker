import type { ProfileRepository } from "../ports/ProfileRepository.ts";

export class ListProgramsUseCase {
  constructor(private readonly repository: ProfileRepository) {}
  execute(signal?: AbortSignal) {
    return this.repository.listPrograms(signal);
  }
}
