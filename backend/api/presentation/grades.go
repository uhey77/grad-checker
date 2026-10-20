package presentation

import (
	"encoding/json"
	"errors"
	"net/http"

	"grad-checker/backend/modules/grades/application/ports"
)

const (
	maxGradeBody     = 256 << 10
	maxGrades        = 1000
	maxAttemptNo     = 20
	minAcademicYear  = 1900
	maxAcademicYear  = 2100
	gradeInputDetail = "成績の形式が不正です。科目・履修回次・成績・年度・学期を確認してください。"
)

var gradeCodes = map[string]bool{"S": true, "A": true, "B": true, "C": true, "D": true, "X": true}

// 本人成績の全集合を取得・置換する。回次の業務ルールはPythonで判定する。
func NewGradeHandler(gateway ports.GradeGateway, origin string, fallback http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/me/grades" {
			fallback.ServeHTTP(w, r)
			return
		}
		w.Header().Set("Cache-Control", "no-store")
		if !allowMethod(w, r, http.MethodGet, http.MethodPut) {
			return
		}
		token, ok := requireSession(w, r)
		if !ok || rejectQuery(w, r) {
			return
		}
		call := ports.GradeCall{Operation: "get", Token: token}
		if r.Method == http.MethodPut {
			csrf, ok := writeToken(w, r, origin)
			if !ok {
				return
			}
			body, ok := readJSONBody(w, r, maxGradeBody, "送信する成績の量が上限を超えています。")
			if !ok {
				return
			}
			gradeSet, detail := decodeGradeSet(body)
			if gradeSet == nil {
				writeError(w, 422, detail)
				return
			}
			call.Operation, call.CSRF, call.GradeSet = "save", csrf, gradeSet
		}
		result, err := gateway.Call(r.Context(), call)
		if err != nil {
			writeGradeError(w, err)
			return
		}
		writeJSON(w, 200, result)
	})
}

func writeGradeError(w http.ResponseWriter, err error) {
	var business *ports.GradeError
	if !errors.As(err, &business) {
		writeError(w, 502, "成績サービスに接続できません。時間をおいて再試行してください。")
		return
	}
	if writeSharedError(w, business.Code, "成績") {
		return
	}
	switch business.Code {
	case "unknown_course":
		writeError(w, 400, "選択した科目が見つかりません。科目一覧を再読み込みしてください。")
	case "duplicate_attempt":
		writeError(w, 422, "同じ科目の履修回次が重複しています。")
	case "invalid_attempt_sequence":
		writeError(w, 422, "履修回次は1から順に入力してください。再履修は不合格（D・X）の後だけ追加できます。")
	default:
		writeError(w, 502, "成績サービスの応答を読み込めません。")
	}
}

func decodeGradeSet(body []byte) (*ports.GradeSet, string) {
	fields, ok := strictObject(body, "expected_revision", "grades")
	if !ok {
		return nil, "成績の送信形式が不正です。expected_revisionとgradesだけを指定してください。"
	}
	revision, ok := decodeInt(fields["expected_revision"], 0, maxSafeRevision)
	var items []json.RawMessage
	if !ok || isNull(fields["grades"]) || json.Unmarshal(fields["grades"], &items) != nil {
		return nil, "成績の送信形式が不正です。expected_revisionとgradesだけを指定してください。"
	}
	if len(items) > maxGrades {
		return nil, "一度に保存できる成績の件数を超えています。"
	}
	grades := make([]ports.GradeAttempt, 0, len(items))
	for _, item := range items {
		grade, ok := decodeGradeAttempt(item)
		if !ok {
			return nil, gradeInputDetail
		}
		grades = append(grades, grade)
	}
	return &ports.GradeSet{ExpectedRevision: revision, Grades: grades}, ""
}

func decodeGradeAttempt(item json.RawMessage) (ports.GradeAttempt, bool) {
	var grade ports.GradeAttempt
	fields, ok := strictObject(item, "course_id", "attempt_no", "result_status", "grade_code", "academic_year", "term_code")
	if !ok {
		return grade, false
	}
	if grade.CourseID, ok = decodeUUID(fields["course_id"]); !ok {
		return grade, false
	}
	if grade.AttemptNo, ok = decodeInt(fields["attempt_no"], 1, maxAttemptNo); !ok {
		return grade, false
	}
	if grade.ResultStatus, ok = decodeString(fields["result_status"]); !ok || (grade.ResultStatus != "finalized" && grade.ResultStatus != "pending") {
		return grade, false
	}
	if !isNull(fields["grade_code"]) {
		code, ok := decodeString(fields["grade_code"])
		if !ok || !gradeCodes[code] {
			return grade, false
		}
		grade.GradeCode = &code
	}
	// 確定した成績は記号を持ち、未確定は記号を持たない。
	if (grade.ResultStatus == "finalized") != (grade.GradeCode != nil) {
		return grade, false
	}
	if !isNull(fields["academic_year"]) {
		year, ok := decodeInt(fields["academic_year"], minAcademicYear, maxAcademicYear)
		if !ok {
			return grade, false
		}
		grade.AcademicYear = &year
	}
	if !isNull(fields["term_code"]) {
		term, ok := decodeString(fields["term_code"])
		if !ok || (term != "first" && term != "second") {
			return grade, false
		}
		grade.TermCode = &term
	}
	return grade, true
}
