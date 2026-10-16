import { createDtoReader } from "../../../shared/infrastructure/dtoReader.ts";
import { ProfileError } from "../application/ProfileUseCases.ts";
import type { Profile, ProgramOption } from "../domain/models.ts";

const { invalid, record, text, nullableText, integer, nullableInteger } =
  createDtoReader(() => {
    throw new ProfileError(502, "所属情報を読み込めません。");
  });

export function toProfile(data: unknown): Profile {
  const value = record(data);
  const profile = {
    studentId: text(value.student_id),
    loginName: text(value.login_name),
    programId: nullableText(value.program_id),
    curriculumId: nullableText(value.curriculum_id),
    dataRevision: integer(value.data_revision),
  };
  if ((profile.programId === null) !== (profile.curriculumId === null))
    return invalid();
  return profile;
}

export function toPrograms(data: unknown): ProgramOption[] {
  const value = record(data);
  if (!Array.isArray(value.programs)) return invalid();
  const ids = new Set<string>();
  return value.programs.map((item) => {
    const p = record(item);
    const status = p.verification_status;
    if (status !== "verified" && status !== "unverified") return invalid();
    const result: ProgramOption = {
      programId: text(p.program_id),
      curriculumId: text(p.curriculum_id),
      facultyName: text(p.faculty_name),
      departmentName: nullableText(p.department_name),
      specializationName: nullableText(p.specialization_name),
      courseName: nullableText(p.course_name),
      curriculumName: text(p.curriculum_name),
      revision: integer(p.revision, 1),
      verificationStatus: status,
      admissionYearFrom: nullableInteger(p.admission_year_from),
      admissionYearTo: nullableInteger(p.admission_year_to),
      sourceDocument: text(p.source_document),
      sourcePages: text(p.source_pages),
    };
    if (
      ids.has(result.curriculumId) ||
      (status === "verified" && result.admissionYearFrom === null) ||
      (result.admissionYearFrom !== null &&
        result.admissionYearTo !== null &&
        result.admissionYearFrom > result.admissionYearTo)
    )
      return invalid();
    ids.add(result.curriculumId);
    return result;
  });
}
