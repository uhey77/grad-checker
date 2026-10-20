// 本人成績の取得・保存ユースケースを言語間で呼び出す契約を定義する。
package ports

import (
	"context"
	"errors"
)

type GradeAttempt struct {
	CourseID     string  `json:"course_id"`
	AttemptNo    int64   `json:"attempt_no"`
	ResultStatus string  `json:"result_status"`
	GradeCode    *string `json:"grade_code"`
	AcademicYear *int64  `json:"academic_year"`
	TermCode     *string `json:"term_code"`
}

type GradeSet struct {
	ExpectedRevision int64          `json:"expected_revision"`
	Grades           []GradeAttempt `json:"grades"`
}

type StudentGrades struct {
	Grades       []GradeAttempt `json:"grades"`
	DataRevision int64          `json:"data_revision"`
}

type GradeCall struct {
	Operation string    `json:"operation"`
	Token     string    `json:"token"`
	CSRF      string    `json:"csrf,omitempty"`
	GradeSet  *GradeSet `json:"grade_set,omitempty"`
}

type GradeError struct {
	Code string `json:"code"`
}

func (e *GradeError) Error() string { return e.Code }

var ErrBackend = errors.New("grade backend unavailable")

type GradeGateway interface {
	Call(context.Context, GradeCall) (StudentGrades, error)
}
