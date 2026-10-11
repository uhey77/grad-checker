import type {
  Program,
  Course,
  Catalog,
} from "../../domain/course-catalog/models";
import type { ProgramDto, CourseDto, CatalogDto } from "./dto";

export function toProgram(dto: ProgramDto): Program {
  return {
    curriculumId: dto.curriculum_id,
    name: dto.name,
    facultyName: dto.faculty_name,
    specializationName: dto.specialization_name,
    courseName: dto.course_name,
    verificationStatus: dto.verification_status,
    admissionYearFrom: dto.admission_year_from,
    admissionYearTo: dto.admission_year_to,
    sourceDocument: dto.source_document,
    sourcePages: dto.source_pages,
  };
}

export function toCourse(dto: CourseDto): Course {
  return {
    id: dto.id,
    code: dto.code,
    name: dto.name,
    credits: dto.credits,
    facultyName: dto.faculty_name,
    departmentName: dto.department_name,
    specializationName: dto.specialization_name,
    teachingTypeLabel: dto.teaching_type_label,
    courseType: dto.course_type,
    classificationPath: dto.classification_path.map(({ id, name }) => ({
      id,
      name,
    })),
    offerings: dto.offerings.map((offering) => ({
      termCode: offering.term_code,
      semesterOrder: offering.semester_order,
      academicYear: offering.academic_year,
      sourceNote: offering.source_note,
    })),
  };
}

export function toCatalog(dto: CatalogDto): Catalog {
  return {
    program: toProgram(dto.program),
    courses: dto.courses.map(toCourse),
  };
}
