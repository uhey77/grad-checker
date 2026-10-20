import { ListProgramsUseCase } from "./application/use_cases/ListProgramsUseCase.ts";
import { GetProfileUseCase } from "./application/use_cases/GetProfileUseCase.ts";
import { SaveProgramUseCase } from "./application/use_cases/SaveProgramUseCase.ts";
import type { ProfileUseCases } from "./application/ports/ProfileUseCases.ts";
import { HttpProfileRepository } from "./infrastructure/external_services/HttpProfileRepository.ts";

export function createProfilesModule(base: string): ProfileUseCases {
  const repository = new HttpProfileRepository(base);
  return {
    listPrograms: new ListProgramsUseCase(repository),
    getProfile: new GetProfileUseCase(repository),
    saveProgram: new SaveProgramUseCase(repository),
  };
}
