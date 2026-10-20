import type { GraduationRepository } from "../ports/GraduationRepository.ts";

export class GetCheckUseCase {
  constructor(private readonly repository: GraduationRepository) {}
  execute(id: string, signal?: AbortSignal) {
    return this.repository.getCheck(id, signal);
  }
}
