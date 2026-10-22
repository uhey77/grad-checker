import type { GraduationRepository } from "../ports/GraduationRepository.ts";

export class GetDashboardUseCase {
  constructor(private readonly repository: GraduationRepository) {}
  execute(signal?: AbortSignal) {
    return this.repository.dashboard(signal);
  }
}
