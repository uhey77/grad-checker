import type { CompletionAnswer } from "../../domain/value_objects/requirements.ts";

import type { GraduationRepository } from "../ports/GraduationRepository.ts";

export class CreateCheckUseCase {
  constructor(private readonly repository: GraduationRepository) {}
  execute(
    expectedRevision: number,
    csrf: string,
    signal?: AbortSignal,
    completionAnswers?: CompletionAnswer[],
  ) {
    return this.repository.createCheck(
      expectedRevision,
      csrf,
      signal,
      completionAnswers,
    );
  }
}
