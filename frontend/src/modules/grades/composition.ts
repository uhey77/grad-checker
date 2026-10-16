import { GradeUseCases } from "./application/GradeUseCases";
import { HttpGradeRepository } from "./infrastructure/HttpGradeRepository";

export function createGradesModule(base: string) {
  return new GradeUseCases(new HttpGradeRepository(base));
}
