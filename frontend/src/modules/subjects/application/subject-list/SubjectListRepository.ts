import type { SubjectList, Program } from "../../domain/subject-list/models";

// 通信方法を問わず、科目一覧の取得に必要な契約。
export interface SubjectListRepository {
  listPrograms(signal: AbortSignal): Promise<Program[]>;
  getSubjectList(
    curriculumId: string,
    signal: AbortSignal,
  ): Promise<SubjectList>;
}
