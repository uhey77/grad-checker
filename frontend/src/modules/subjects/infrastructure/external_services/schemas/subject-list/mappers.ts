import type { Program, Subject } from "../../../../domain/entities/subject.ts";
import type { SubjectList } from "../../../../application/dto/subjectList.ts";
import type { ProgramDto, SubjectDto, SubjectListDto } from "./dto.ts";

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

export function toSubject(dto: SubjectDto): Subject {
  return {
    id: dto.id,
    code: dto.code,
    name: dto.name,
    credits: dto.credits,
    facultyName: dto.faculty_name,
    departmentName: dto.department_name,
    specializationName: dto.specialization_name,
    teachingTypeLabel: dto.teaching_type_label,
    subjectType: dto.course_type,
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

export function toSubjectList(dto: SubjectListDto): SubjectList {
  return {
    program: toProgram(dto.program),
    subjects: dto.courses.map(toSubject),
  };
}
