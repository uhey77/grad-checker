export interface ProgramDto {
  curriculum_id: string;
  name: string;
  faculty_name: string;
  specialization_name: string | null;
  course_name: string | null;
  verification_status: "unverified" | "verified";
  admission_year_from: number | null;
  admission_year_to: number | null;
  source_document: string;
  source_pages: string;
}

export interface OfferingDto {
  term_code: string;
  semester_order: number;
  academic_year: number | null;
  source_note: string | null;
}

export interface CourseDto {
  id: string;
  code: string;
  name: string;
  credits: number;
  faculty_name: string;
  department_name: string | null;
  specialization_name: string | null;
  teaching_type_label: string;
  course_type: "required" | "selective" | "elective";
  classification_path: { id: string; name: string }[];
  offerings: OfferingDto[];
}

export interface CatalogDto {
  program: ProgramDto;
  courses: CourseDto[];
}
