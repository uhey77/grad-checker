import { GetGradesUseCase } from "./application/use_cases/GetGradesUseCase.ts";
import { SaveGradesUseCase } from "./application/use_cases/SaveGradesUseCase.ts";
import type { GradeUseCases } from "./application/ports/GradeUseCases.ts";
import { HttpGradeRepository } from "./infrastructure/HttpGradeRepository.ts";

export function createGradesModule(base: string): GradeUseCases {
  const repository = new HttpGradeRepository(base);
  return {
    getGrades: new GetGradesUseCase(repository),
    saveGrades: new SaveGradesUseCase(repository),
  };
}
