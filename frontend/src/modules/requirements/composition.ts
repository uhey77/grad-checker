import { GetDashboardUseCase } from "./application/use_cases/GetDashboardUseCase.ts";
import { EvaluateGraduationUseCase } from "./application/use_cases/EvaluateGraduationUseCase.ts";
import { CreateCheckUseCase } from "./application/use_cases/CreateCheckUseCase.ts";
import { ListChecksUseCase } from "./application/use_cases/ListChecksUseCase.ts";
import { GetCheckUseCase } from "./application/use_cases/GetCheckUseCase.ts";
import type { GraduationUseCases } from "./application/ports/GraduationUseCases.ts";
import { HttpGraduationRepository } from "./infrastructure/external_services/HttpGraduationRepository.ts";

export function createRequirementsModule(base: string): GraduationUseCases {
  const repository = new HttpGraduationRepository(base);
  return {
    dashboard: new GetDashboardUseCase(repository),
    evaluate: new EvaluateGraduationUseCase(repository),
    createCheck: new CreateCheckUseCase(repository),
    listChecks: new ListChecksUseCase(repository),
    getCheck: new GetCheckUseCase(repository),
  };
}
