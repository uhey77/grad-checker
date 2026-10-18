import { createDtoReader } from "../../../shared/infrastructure/dtoReader.ts";
import { GraduationError } from "../application/GraduationUseCases.ts";
import type {
  CheckPage,
  CheckSummary,
  CheckedGrade,
  CreditSummary,
  DashboardResult,
  GraduationResult,
  Judgment,
  RequirementResult,
  SavedCheck,
} from "../domain/models.ts";

const { invalid, record, list, text, integer, nullableText } = createDtoReader(
  () => {
    throw new GraduationError(502, "卒業要件の判定結果を読み込めません。");
  },
);

function judgment(value: unknown): Judgment {
  return value === "pass" || value === "fail" ? value : invalid();
}

function summary(data: unknown): CreditSummary {
  const value = record(data);
  return {
    requiredCredits: integer(value.required_credits),
    earnedCredits: integer(value.earned_credits),
    creditedCredits: integer(value.credited_credits),
    shortage: integer(value.shortage),
    result: judgment(value.result),
  };
}

const kinds = [
  "total",
  "classification_total",
  "required_courses",
  "selective_group",
  "subminimum",
  "elective_total",
] as const;

function condition(data: unknown): RequirementResult {
  const value = record(data);
  const kind = value.kind as RequirementResult["kind"];
  if (!kinds.includes(kind)) return invalid();
  return {
    ...summary(value),
    id: text(value.id),
    code: text(value.code),
    name: text(value.name),
    kind,
    parentId: nullableText(value.parent_id),
    classificationId: nullableText(value.classification_id),
  };
}

function evaluationSummary(data: unknown) {
  const value = record(data);
  const curriculum = record(value.curriculum);
  const evaluatedAt = text(value.evaluated_at);
  if (
    (curriculum.verification_status !== "verified" &&
      curriculum.verification_status !== "unverified") ||
    !Number.isFinite(Date.parse(evaluatedAt))
  )
    return invalid();
  return {
    result: judgment(value.result),
    dataRevision: integer(value.data_revision),
    ruleRevisions: Object.fromEntries(
      Object.entries(record(value.rule_revisions)).map(([id, revision]) => [
        id,
        integer(revision, 1),
      ]),
    ),
    evaluatedAt,
    curriculum: {
      id: text(curriculum.id),
      name: text(curriculum.name),
      revision: integer(curriculum.revision, 1),
      sourceDocument: text(curriculum.source_document),
      sourcePages: text(curriculum.source_pages),
    },
    total: summary(value.total),
    warnings: list(value.warnings).map<GraduationResult["warnings"][number]>(
      (warning) =>
        warning === "provisional_external_allocation" ? warning : invalid(),
    ),
  };
}

export function toDashboardResult(data: unknown): DashboardResult {
  const value = record(data);
  const common = evaluationSummary(value);
  const curriculumRevision = integer(value.curriculum_revision, 1);
  const categories = list(value.categories).map(condition);
  if (
    curriculumRevision !== common.curriculum.revision ||
    categories.some((row) => row.kind !== "classification_total") ||
    new Set(categories.map((row) => row.id)).size !== categories.length
  )
    return invalid();
  return {
    ...common,
    curriculumRevision,
    gradeCount: integer(value.grade_count),
    categories,
  };
}

export function toGraduationResult(data: unknown): GraduationResult {
  const value = record(data);
  const requirements = list(value.requirements).map(condition);
  if (
    !requirements.length ||
    new Set(requirements.map((r) => r.id)).size !== requirements.length
  )
    return invalid();
  return {
    ...evaluationSummary(value),
    externalAllocations: list(value.external_allocations).map((data) => {
      const row = record(data);
      const earnedCredits = integer(row.earned_credits);
      const creditedCredits = integer(row.credited_credits);
      const freeCredits = integer(row.free_credits);
      if (creditedCredits + freeCredits !== earnedCredits) return invalid();
      return {
        ruleId: text(row.rule_id),
        targetClassificationId: text(row.target_classification_id),
        targetName: text(row.target_name),
        earnedCredits,
        creditedCredits,
        freeCredits,
      };
    }),
    requirements,
    missingRequiredCourses: list(value.missing_required_courses).map((data) => {
      const course = record(data);
      return {
        courseId: text(course.course_id),
        name: text(course.name),
        credits: integer(course.credits, 1),
      };
    }),
    allocations: list(value.allocations).map((data) => {
      const allocation = record(data);
      return {
        requirementId: text(allocation.requirement_id),
        transferredCredits: integer(allocation.transferred_credits),
      };
    }),
  };
}

function timestamp(value: unknown): string {
  const created = text(value);
  return Number.isFinite(Date.parse(created)) ? created : invalid();
}

function checkSummary(data: unknown): CheckSummary {
  const value = record(data);
  const curriculum = record(value.curriculum);
  return {
    id: text(value.id),
    createdAt: timestamp(value.created_at),
    dataRevision: integer(value.data_revision),
    result: judgment(value.result),
    curriculum: {
      id: text(curriculum.id),
      code: text(curriculum.code),
      name: text(curriculum.name),
      revision: integer(curriculum.revision, 1),
    },
    total: summary(value.total),
  };
}

export function toCheckPage(data: unknown): CheckPage {
  const value = record(data);
  const checks = list(value.checks).map(checkSummary);
  const limit = integer(value.limit, 1);
  const offset = integer(value.offset);
  const totalCount = integer(value.total_count);
  if (
    checks.length > limit ||
    (checks.length > 0 && offset + checks.length > totalCount)
  )
    return invalid();
  return { checks, limit, offset, totalCount };
}

const gradeCodes = ["S", "A", "B", "C", "D", "X"] as const;

export function toSavedCheck(data: unknown): SavedCheck {
  const value = record(data);
  const input = record(value.input);
  const resultData = record(value.result);
  const result = toGraduationResult(resultData);
  const createdAt = timestamp(value.created_at);
  // 科目名は保存済みの判定結果から引き、現在の科目マスタを参照しない。
  const names = new Map(
    list(resultData.courses).map((data) => {
      const course = record(data);
      return [text(course.course_id), text(course.name)] as const;
    }),
  );
  const grades = list(input.grades).map((data): CheckedGrade => {
    const grade = record(data);
    const courseId = text(grade.course_id);
    const resultStatus = grade.result_status;
    const gradeCode = grade.grade_code as CheckedGrade["gradeCode"];
    if (
      (resultStatus === "finalized" && !gradeCodes.includes(gradeCode!)) ||
      (resultStatus === "pending" && gradeCode !== null) ||
      (resultStatus !== "finalized" && resultStatus !== "pending")
    )
      return invalid();
    return {
      courseId,
      courseName: names.get(courseId) ?? null,
      attemptNo: integer(grade.attempt_no, 1),
      resultStatus,
      gradeCode,
    };
  });
  const dataRevision = integer(input.data_revision);
  // 入力と結果は同じ時刻・同じ成績版のスナップショットから作られている。
  if (
    result.dataRevision !== dataRevision ||
    Date.parse(result.evaluatedAt) !== Date.parse(createdAt)
  )
    return invalid();
  return {
    id: text(value.id),
    createdAt,
    input: {
      programId: text(input.program_id),
      curriculumId: text(input.curriculum_id),
      dataRevision,
      grades,
    },
    result,
  };
}
