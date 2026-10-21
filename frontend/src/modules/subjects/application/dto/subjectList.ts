import type { Program } from "../../domain/entities/subject.ts";
import type { Subject } from "../../domain/entities/subject.ts";

export interface SubjectList {
  program: Program;
  subjects: Subject[];
}
