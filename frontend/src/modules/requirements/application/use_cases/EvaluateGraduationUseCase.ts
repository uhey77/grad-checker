import type { GraduationRepository } from "../ports/GraduationRepository.ts";

export class EvaluateGraduationUseCase {
  constructor(private readonly repository: GraduationRepository) {}
  execute(signal?: AbortSignal) {
    return this.repository.evaluate(signal);
  }
}
