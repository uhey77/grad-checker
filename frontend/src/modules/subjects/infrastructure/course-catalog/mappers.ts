import { CourseCatalogError } from "../../application/errors/CourseCatalogError.ts";
import type {
  CatalogCategory,
  CatalogCourse,
  CatalogCurriculum,
  CourseCatalog,
  CourseType,
} from "../../domain/course-catalog/models.ts";

function invalid(): never {
  throw new CourseCatalogError(502, "科目データを読み込めません。");
}
function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value))
    return invalid();
  return value as Record<string, unknown>;
}
function list(value: unknown): unknown[] {
  return Array.isArray(value) ? value : invalid();
}
function text(value: unknown): string {
  if (typeof value !== "string" || !value.trim()) return invalid();
  return value;
}
function nullableText(value: unknown): string | null {
  return value === null ? null : text(value);
}
function integer(value: unknown, minimum = 0): number {
  if (
    typeof value !== "number" ||
    !Number.isSafeInteger(value) ||
    value < minimum
  )
    return invalid();
  return value;
}
function nullableInteger(value: unknown, minimum = 1): number | null {
  return value === null ? null : integer(value, minimum);
}

function toCurriculum(data: unknown): CatalogCurriculum {
  const value = record(data);
  const status = value.verification_status;
  if (status !== "verified" && status !== "unverified") return invalid();
  return {
    curriculumId: text(value.curriculum_id),
    name: text(value.name),
    verificationStatus: status,
    admissionYearFrom: nullableInteger(value.admission_year_from),
    admissionYearTo: nullableInteger(value.admission_year_to),
    sourceDocument: text(value.source_document),
    sourcePages: text(value.source_pages),
  };
}

function toCategory(data: unknown): CatalogCategory {
  const value = record(data);
  return {
    id: text(value.id),
    code: text(value.code),
    name: text(value.name),
    parentId: nullableText(value.parent_id),
    level: integer(value.level),
    displayOrder: integer(value.display_order),
  };
}

function toCourse(data: unknown): CatalogCourse {
  const value = record(data);
  const placement = value.placement === null ? null : record(value.placement);
  const courseType = placement?.course_type;
  if (
    placement &&
    courseType !== "required" &&
    courseType !== "selective" &&
    courseType !== "elective"
  )
    return invalid();
  return {
    courseId: text(value.course_id),
    code: text(value.code),
    name: text(value.name),
    credits: integer(value.credits, 1),
    offeringFacultyName: text(value.offering_faculty_name),
    offeringDepartmentName: nullableText(value.offering_department_name),
    offeringSpecializationName: nullableText(
      value.offering_specialization_name,
    ),
    teachingTypeLabel: text(value.teaching_type_label),
    offerings: list(value.offerings).map((item) => {
      const offering = record(item);
      return {
        termCode: text(offering.term_code),
        semesterOrder: integer(offering.semester_order, 1),
        academicYear: nullableInteger(offering.academic_year),
        sourceNote: nullableText(offering.source_note),
      };
    }),
    placement:
      placement === null
        ? null
        : {
            classificationPath: list(placement.classification_path).map(
              (item) => {
                const classification = record(item);
                return {
                  id: text(classification.id),
                  name: text(classification.name),
                };
              },
            ),
            courseType: courseType as CourseType,
          },
  };
}

// 科目一覧と分類一覧が同じ本人課程の応答であることを確認して結合する。
export function toCourseCatalog(
  coursesData: unknown,
  categoriesData: unknown,
): CourseCatalog {
  const courses = record(coursesData);
  const categories = record(categoriesData);
  const curriculum = toCurriculum(courses.curriculum);
  if (
    toCurriculum(categories.curriculum).curriculumId !== curriculum.curriculumId
  )
    return invalid();
  return {
    curriculum,
    categories: list(categories.categories).map(toCategory),
    courses: list(courses.courses).map(toCourse),
  };
}
