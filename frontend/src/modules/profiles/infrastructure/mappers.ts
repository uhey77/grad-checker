import { createDtoReader } from "../../../shared/infrastructure/dtoReader.ts";
import { ProfileError } from "../application/ProfileUseCases.ts";
import type {
  CompletionPolicy,
  Profile,
  ProgramOption,
} from "../domain/models.ts";

const { invalid, record, list, text, nullableText, integer, nullableInteger } =
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
      completionPolicy:
        p.completion_policy == null ? undefined : policy(p.completion_policy),
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

function policy(data: unknown): CompletionPolicy {
  const p = record(data);
  function status(value: unknown) {
    return value === "verified" || value === "unverified" ? value : invalid();
  }
  const level = p.degree_level,
    campus = p.campus;
  if (
    (level !== "bachelor" && level !== "master" && level !== "doctoral") ||
    (campus !== "hachioji" && campus !== "kamata")
  )
    return invalid();
  return {
    degreeLevel: level,
    campus,
    catalogStatus: status(p.catalog_status),
    requirementsStatus: status(p.requirements_status),
    rulesStatus: status(p.rules_status),
    unresolvedReasons: list(p.unresolved_reasons).map(text),
    sourceDocument: text(p.source_document),
    sourcePages: text(p.source_pages),
    conditions: list(p.non_credit_conditions).map((data) => {
      const c = record(data);
      return {
        code: text(c.code),
        name: text(c.name),
        sourceDocument: text(c.source_document),
        sourcePages: text(c.source_pages),
      };
    }),
  };
}
