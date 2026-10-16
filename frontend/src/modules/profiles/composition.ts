import { ProfileUseCases } from "./application/ProfileUseCases";
import { HttpProfileRepository } from "./infrastructure/HttpProfileRepository";

export function createProfilesModule(base: string) {
  return new ProfileUseCases(new HttpProfileRepository(base));
}
