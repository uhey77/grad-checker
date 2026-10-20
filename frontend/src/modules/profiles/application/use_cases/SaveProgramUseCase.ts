import type { ProgramSelection } from "../../domain/models.ts";
import type { ProfileRepository } from "../ports/ProfileRepository.ts";

export class SaveProgramUseCase {
  constructor(private readonly repository: ProfileRepository) {}
  execute(selection: ProgramSelection, csrf: string, signal?: AbortSignal) {
    return this.repository.saveProgram(selection, csrf, signal);
  }
}
