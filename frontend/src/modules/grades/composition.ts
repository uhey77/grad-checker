import { GetGradesUseCase } from "./application/use_cases/GetGradesUseCase.ts";
import { ReadGradeScreenshotUseCase } from "./application/use_cases/ReadGradeScreenshotUseCase.ts";
import { SaveGradesUseCase } from "./application/use_cases/SaveGradesUseCase.ts";
import type { GradeUseCases } from "./application/ports/GradeUseCases.ts";
import { HttpGradeRepository } from "./infrastructure/external_services/HttpGradeRepository.ts";
import { TesseractGradeScreenshotReader } from "./infrastructure/external_services/TesseractGradeScreenshotReader.ts";

export function createGradesModule(
  base: string,
  ocrAssetBase: string,
): GradeUseCases {
  const repository = new HttpGradeRepository(base);
  return {
    getGrades: new GetGradesUseCase(repository),
    saveGrades: new SaveGradesUseCase(repository),
    readScreenshot: new ReadGradeScreenshotUseCase(
      new TesseractGradeScreenshotReader(ocrAssetBase),
    ),
  };
}
