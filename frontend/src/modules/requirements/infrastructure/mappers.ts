import { createDtoReader } from "../../../shared/infrastructure/dtoReader.ts";
import { GraduationError } from "../application/GraduationUseCases.ts";
import type {
  CreditSummary,
  GraduationResult,
  Judgment,
  RequirementResult,
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

export function toGraduationResult(data: unknown): GraduationResult {
  const value = record(data);
  const curriculum = record(value.curriculum);
  const evaluatedAt = text(value.evaluated_at);
  if (
    (curriculum.verification_status !== "verified" &&
      curriculum.verification_status !== "unverified") ||
    !Number.isFinite(Date.parse(evaluatedAt))
  )
    return invalid();
  const requirements = list(value.requirements).map(condition);
  if (
    !requirements.length ||
    new Set(requirements.map((r) => r.id)).size !== requirements.length
  )
    return invalid();
  return {
    result: judgment(value.result),
    dataRevision: integer(value.data_revision),
    evaluatedAt,
    curriculum: {
      id: text(curriculum.id),
      name: text(curriculum.name),
      revision: integer(curriculum.revision, 1),
      sourceDocument: text(curriculum.source_document),
      sourcePages: text(curriculum.source_pages),
    },
    total: summary(value.total),
    warnings: list(value.warnings).map((warning) =>
      warning === "provisional_external_allocation" ? warning : invalid(),
    ),
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
