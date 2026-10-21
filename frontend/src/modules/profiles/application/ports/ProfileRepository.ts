import type { Profile } from "../../domain/entities/profile.ts";
import type { ProgramOption } from "../../domain/entities/program.ts";
import type { ProgramSelection } from "../dto/profile.ts";
export interface ProfileRepository {
  listPrograms(signal?: AbortSignal): Promise<ProgramOption[]>;
  getProfile(signal?: AbortSignal): Promise<Profile>;
  saveProgram(
    selection: ProgramSelection,
    csrf: string,
    signal?: AbortSignal,
  ): Promise<Profile>;
}
