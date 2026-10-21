import type { ListSubjectProgramsUseCase } from "../use_cases/ListSubjectProgramsUseCase.ts";
import type { GetSubjectListUseCase } from "../use_cases/GetSubjectListUseCase.ts";

export interface SubjectListUseCases {
  readonly listPrograms: Pick<ListSubjectProgramsUseCase, "execute">;
  readonly getSubjectList: Pick<GetSubjectListUseCase, "execute">;
}
