import { GraduationUseCases } from "./application/GraduationUseCases.ts";
import { HttpGraduationRepository } from "./infrastructure/HttpGraduationRepository.ts";

export function createRequirementsModule(base: string) {
  return new GraduationUseCases(new HttpGraduationRepository(base));
}
