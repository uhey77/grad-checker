export type { GraduationUseCases } from "./application/ports/GraduationUseCases.ts";
export { GraduationError } from "./application/errors/GraduationError.ts";
export type { GraduationRepository } from "./application/ports/GraduationRepository.ts";
export type { CheckPageRequest } from "./application/dto/CheckPageRequest.ts";
export {
  buildRequirementMatrix,
  type RequirementMatrixRow,
} from "./application/services/buildRequirementMatrix.ts";
export { filterRequirements } from "./application/services/filterRequirements.ts";
export type {
  GraduationResult,
  DashboardResult,
  CheckSummary,
  CheckPage,
  CheckedGrade,
  SavedCheck,
} from "./application/dto/results.ts";
export type {
  CourseRecommendation,
  RequirementResult,
} from "./domain/entities/requirements.ts";
export type {
  CreditSummary,
  Judgment,
} from "./domain/value_objects/requirements.ts";

export type { CompletionAnswer } from "./domain/value_objects/requirements.ts";
export type { CompletionCondition } from "./domain/entities/requirements.ts";

export { GetDashboardUseCase } from "./application/use_cases/GetDashboardUseCase.ts";
export { EvaluateGraduationUseCase } from "./application/use_cases/EvaluateGraduationUseCase.ts";
export { CreateCheckUseCase } from "./application/use_cases/CreateCheckUseCase.ts";
export { ListChecksUseCase } from "./application/use_cases/ListChecksUseCase.ts";
export { GetCheckUseCase } from "./application/use_cases/GetCheckUseCase.ts";
