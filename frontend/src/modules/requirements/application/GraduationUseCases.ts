import type { GraduationResult } from "../domain/models.ts";

export class GraduationError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "GraduationError";
  }
}

export interface GraduationRepository {
  evaluate(signal?: AbortSignal): Promise<GraduationResult>;
}

export class GraduationUseCases implements GraduationRepository {
  constructor(private readonly repository: GraduationRepository) {}
  evaluate(signal?: AbortSignal) {
    return this.repository.evaluate(signal);
  }
}
