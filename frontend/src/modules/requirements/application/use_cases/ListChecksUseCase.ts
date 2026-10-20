import type { CheckPageRequest } from "../dto/CheckPageRequest.ts";
import type { GraduationRepository } from "../ports/GraduationRepository.ts";

export class ListChecksUseCase {
  constructor(private readonly repository: GraduationRepository) {}
  execute(page: CheckPageRequest, signal?: AbortSignal) {
    return this.repository.listChecks(page, signal);
  }
}
