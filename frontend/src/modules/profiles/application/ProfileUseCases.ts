import type {
  Profile,
  ProgramOption,
  ProgramSelection,
} from "../domain/models.ts";

export class ProfileError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

export interface ProfileRepository {
  listPrograms(signal?: AbortSignal): Promise<ProgramOption[]>;
  getProfile(signal?: AbortSignal): Promise<Profile>;
  saveProgram(
    selection: ProgramSelection,
    csrf: string,
    signal?: AbortSignal,
  ): Promise<Profile>;
}

export class ProfileUseCases implements ProfileRepository {
  constructor(private readonly repository: ProfileRepository) {}
  listPrograms(signal?: AbortSignal) {
    return this.repository.listPrograms(signal);
  }
  getProfile(signal?: AbortSignal) {
    return this.repository.getProfile(signal);
  }
  saveProgram(selection: ProgramSelection, csrf: string, signal?: AbortSignal) {
    return this.repository.saveProgram(selection, csrf, signal);
  }
}
