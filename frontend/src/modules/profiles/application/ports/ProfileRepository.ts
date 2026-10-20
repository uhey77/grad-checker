import type {
  Profile,
  ProgramOption,
  ProgramSelection,
} from "../../domain/models.ts";
export interface ProfileRepository {
  listPrograms(signal?: AbortSignal): Promise<ProgramOption[]>;
  getProfile(signal?: AbortSignal): Promise<Profile>;
  saveProgram(
    selection: ProgramSelection,
    csrf: string,
    signal?: AbortSignal,
  ): Promise<Profile>;
}
