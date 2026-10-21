import type { SubjectList } from "../dto/subjectList.ts";
import type { Program } from "../../domain/entities/subject.ts";

// 通信方法を問わず、科目一覧の取得に必要な契約。
export interface SubjectListRepository {
  listPrograms(signal: AbortSignal): Promise<Program[]>;
  getSubjectList(
    curriculumId: string,
    signal: AbortSignal,
  ): Promise<SubjectList>;
}
