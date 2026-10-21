package schemas

import (
	"encoding/json"

	"grad-checker/backend/modules/grades/application/ports"
)

const (
	MaxGradeBody     = 256 << 10
	MaxGrades        = 1000
	MaxAttemptNo     = 20
	MinAcademicYear  = 1900
	MaxAcademicYear  = 2100
	GradeInputDetail = "成績の形式が不正です。科目・履修回次・成績・年度・学期を確認してください。"
)

var GradeCodes = map[string]bool{"S": true, "A": true, "B": true, "C": true, "D": true, "X": true}

func DecodeGradeSet(body []byte) (*ports.GradeSet, string) {
	fields, ok := StrictObject(body, "expected_revision", "grades")
	if !ok {
		return nil, "成績の送信形式が不正です。expected_revisionとgradesだけを指定してください。"
	}
	revision, ok := DecodeInt(fields["expected_revision"], 0, MaxSafeRevision)
	var items []json.RawMessage
	if !ok || IsNull(fields["grades"]) || json.Unmarshal(fields["grades"], &items) != nil {
		return nil, "成績の送信形式が不正です。expected_revisionとgradesだけを指定してください。"
	}
	if len(items) > MaxGrades {
		return nil, "一度に保存できる成績の件数を超えています。"
	}
	grades := make([]ports.GradeAttempt, 0, len(items))
	for _, item := range items {
		grade, ok := DecodeGradeAttempt(item)
		if !ok {
			return nil, GradeInputDetail
		}
		grades = append(grades, grade)
	}
	return &ports.GradeSet{ExpectedRevision: revision, Grades: grades}, ""
}

func DecodeGradeAttempt(item json.RawMessage) (ports.GradeAttempt, bool) {
	var grade ports.GradeAttempt
	fields, ok := StrictObject(item, "course_id", "attempt_no", "result_status", "grade_code", "academic_year", "term_code")
	if !ok {
		return grade, false
	}
	if grade.CourseID, ok = DecodeUUID(fields["course_id"]); !ok {
		return grade, false
	}
	if grade.AttemptNo, ok = DecodeInt(fields["attempt_no"], 1, MaxAttemptNo); !ok {
		return grade, false
	}
	if grade.ResultStatus, ok = DecodeString(fields["result_status"]); !ok || (grade.ResultStatus != "finalized" && grade.ResultStatus != "pending") {
		return grade, false
	}
	if !IsNull(fields["grade_code"]) {
		code, ok := DecodeString(fields["grade_code"])
		if !ok || !GradeCodes[code] {
			return grade, false
		}
		grade.GradeCode = &code
	}
	// 確定した成績は記号を持ち、未確定は記号を持たない。
	if (grade.ResultStatus == "finalized") != (grade.GradeCode != nil) {
		return grade, false
	}
	if !IsNull(fields["academic_year"]) {
		year, ok := DecodeInt(fields["academic_year"], MinAcademicYear, MaxAcademicYear)
		if !ok {
			return grade, false
		}
		grade.AcademicYear = &year
	}
	if !IsNull(fields["term_code"]) {
		term, ok := DecodeString(fields["term_code"])
		if !ok || (term != "first" && term != "second") {
			return grade, false
		}
		grade.TermCode = &term
	}
	return grade, true
}
