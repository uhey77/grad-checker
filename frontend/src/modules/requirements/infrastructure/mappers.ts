import { createDtoReader } from "../../../shared/infrastructure/dtoReader.ts";
import { GraduationError } from "../application/GraduationUseCases.ts";
import type {
  CheckPage,
  CompletionCondition,
  CheckSummary,
  CheckedGrade,
  CreditSummary,
  CourseRecommendation,
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
  return value === "pass" || value === "fail" || value === "pending"
    ? value
    : invalid();
}

function summary(data: unknown): CreditSummary {
  const value = record(data);
  const result = judgment(value.result);
  if (result === "pending") return invalid();
  return {
    requiredCredits: integer(value.required_credits),
    earnedCredits: integer(value.earned_credits),
    creditedCredits: integer(value.credited_credits),
    shortage: integer(value.shortage),
    result,
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
    ...completion(value),
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

function recommendations(data: unknown): CourseRecommendation[] {
  const rows = list(data).map((data): CourseRecommendation => {
    const row = record(data);
    const status = row.status;
    if (
      (status !== "not_earned" &&
        status !== "pending" &&
        status !== "not_taken") ||
      typeof row.is_required !== "boolean"
    )
      return invalid();
    const contributions = list(row.contributions).map((data) => {
      const reason = record(data);
      return {
        requirementId: text(reason.requirement_id),
        code: text(reason.code),
        name: text(reason.name),
        shortageReduction: integer(reason.shortage_reduction, 1),
        reason: text(reason.reason),
      };
    });
    if (
      !contributions.length ||
      new Set(contributions.map((r) => r.requirementId)).size !==
        contributions.length
    )
      return invalid();
    return {
      courseId: text(row.course_id),
      name: text(row.name),
      credits: integer(row.credits, 1),
      status,
      isRequired: row.is_required,
      offerings: list(row.offerings).map((data) => {
        const offering = record(data);
        return {
          termCode: text(offering.term_code),
          semesterOrder: integer(offering.semester_order, 1),
          academicYear:
            offering.academic_year === null
              ? null
              : integer(offering.academic_year, 1),
          sourceNote: nullableText(offering.source_note),
        };
      }),
      contributions,
    };
  });
  if (new Set(rows.map((row) => row.courseId)).size !== rows.length)
    return invalid();
  return rows;
}

export function toGraduationResult(data: unknown): GraduationResult {
  return graduationResult(data, false);
}

function graduationResult(data: unknown, legacy: boolean): GraduationResult {
  const value = record(data);
  const requirements = list(value.requirements).map(condition);
  if (
    !requirements.length ||
    new Set(requirements.map((r) => r.id)).size !== requirements.length
  )
    return invalid();
  return {
    ...evaluationSummary(value),
    recommendations:
      legacy && value.recommendations == null
        ? null
        : recommendations(value.recommendations),
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
  const result = graduationResult(resultData, true);
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

function completion(value: Record<string, unknown>): {
  degreeLevel: GraduationResult["degreeLevel"];
  completionConditions: CompletionCondition[];
} {
  const level = value.degree_level;
  if (
    level !== undefined &&
    level !== "bachelor" &&
    level !== "master" &&
    level !== "doctoral"
  )
    return invalid();
  const conditions: CompletionCondition[] =
    value.completion_conditions === undefined
      ? []
      : list(value.completion_conditions).map((data) => {
          const c = record(data),
            status = c.status;
          if (status !== "met" && status !== "not_met" && status !== "unknown")
            return invalid();
          return {
            code: text(c.code),
            name: text(c.name),
            status,
            sourceDocument: text(c.source_document),
            sourcePages: text(c.source_pages),
          };
        });
  if (new Set(conditions.map((c) => c.code)).size !== conditions.length)
    return invalid();
  return { degreeLevel: level, completionConditions: conditions };
}
