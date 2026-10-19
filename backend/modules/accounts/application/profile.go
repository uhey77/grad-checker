package application

import (
	"context"
	"encoding/json"
)

type ProgramOption struct {
	CompletionPolicy   json.RawMessage `json:"completion_policy"`
	ProgramID          string          `json:"program_id"`
	CurriculumID       string          `json:"curriculum_id"`
	FacultyName        string          `json:"faculty_name"`
	DepartmentName     *string         `json:"department_name"`
	SpecializationName *string         `json:"specialization_name"`
	CourseName         *string         `json:"course_name"`
	CurriculumName     string          `json:"curriculum_name"`
	Revision           int64           `json:"revision"`
	VerificationStatus string          `json:"verification_status"`
	AdmissionYearFrom  *int            `json:"admission_year_from"`
	AdmissionYearTo    *int            `json:"admission_year_to"`
	SourceDocument     string          `json:"source_document"`
	SourcePages        string          `json:"source_pages"`
}

type Profile struct {
	StudentID    string  `json:"student_id"`
	LoginName    string  `json:"login_name"`
	ProgramID    *string `json:"program_id"`
	CurriculumID *string `json:"curriculum_id"`
	DataRevision int64   `json:"data_revision"`
}

type ProgramSelection struct {
	ProgramID        string `json:"program_id"`
	CurriculumID     string `json:"curriculum_id"`
	ExpectedRevision int64  `json:"expected_revision"`
}

type ProfileCall struct {
	Operation string            `json:"operation"`
	Token     string            `json:"token"`
	CSRF      string            `json:"csrf,omitempty"`
	Selection *ProgramSelection `json:"selection,omitempty"`
}

type ProfileResult struct {
	Programs *[]ProgramOption `json:"programs,omitempty"`
	Profile  *Profile         `json:"profile,omitempty"`
}

type ProfileGateway interface {
	Call(context.Context, ProfileCall) (ProfileResult, error)
}
