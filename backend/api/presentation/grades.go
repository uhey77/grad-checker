package presentation

import (
	"bytes"
	"encoding/json"
	"errors"
	"io"
	"mime"
	"net/http"

	"grad-checker/backend/modules/grades/application"
)

const (
	maxGradeBody     = 256 << 10
	maxGrades        = 1000
	maxAttemptNo     = 20
	minAcademicYear  = 1900
	maxAcademicYear  = 2100
	maxSafeRevision  = 9007199254740990
	gradeInputDetail = "成績の形式が不正です。科目・履修回次・成績・年度・学期を確認してください。"
)

var gradeCodes = map[string]bool{"S": true, "A": true, "B": true, "C": true, "D": true, "X": true}

// sessionTokenは本人を決めるセッション原値をCookieから取り出す。本人IDは外部入力から受け取らない。
func sessionToken(r *http.Request) (string, bool) {
	cookie, err := r.Cookie(sessionCookie)
	if err != nil || len(cookie.Value) != 43 {
		return "", false
	}
	return cookie.Value, true
}

// 本人成績の全集合を取得・置換する。回次の業務ルールはPythonで判定する。
func NewGradeHandler(gateway application.GradeGateway, origin string, fallback http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/me/grades" {
			fallback.ServeHTTP(w, r)
			return
		}
		w.Header().Set("Cache-Control", "no-store")
		if r.Method != http.MethodGet && r.Method != http.MethodPut {
			w.Header().Set("Allow", "GET, PUT")
			writeError(w, 405, "HTTPメソッドが不正です。")
			return
		}
		token, ok := sessionToken(r)
		if !ok {
			writeError(w, 401, "ログインしてください。")
			return
		}
		if r.URL.RawQuery != "" {
			writeError(w, 422, "クエリパラメーターは指定できません。")
			return
		}
		call := application.GradeCall{Operation: "get", Token: token}
		if r.Method == http.MethodPut {
			call.Operation, call.CSRF = "save", r.Header.Get("X-CSRF-Token")
			if r.Header.Get("Origin") != origin || len(call.CSRF) != 64 {
				writeError(w, 403, "操作を確認できません。画面を再読み込みしてください。")
				return
			}
			media, _, err := mime.ParseMediaType(r.Header.Get("Content-Type"))
			if err != nil || media != "application/json" {
				writeError(w, 415, "成績はJSON形式で送信してください。")
				return
			}
			body, err := io.ReadAll(http.MaxBytesReader(w, r.Body, maxGradeBody))
			if err != nil {
				writeError(w, 413, "送信する成績の量が上限を超えています。")
				return
			}
			gradeSet, detail := decodeGradeSet(body)
			if gradeSet == nil {
				writeError(w, 422, detail)
				return
			}
			call.GradeSet = gradeSet
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
	var business *application.GradeError
	if !errors.As(err, &business) {
		writeError(w, 502, "成績サービスに接続できません。時間をおいて再試行してください。")
		return
	}
	switch business.Code {
	case "invalid_credentials", "invalid_csrf":
		writeAuthError(w, business.Code)
	case "student_not_found":
		writeError(w, 401, "ログインしてください。")
	case "unknown_course":
		writeError(w, 400, "選択した科目が見つかりません。科目一覧を再読み込みしてください。")
	case "duplicate_attempt":
		writeError(w, 422, "同じ科目の履修回次が重複しています。")
	case "invalid_attempt_sequence":
		writeError(w, 422, "履修回次は1から順に入力してください。再履修は不合格（D・X）の後だけ追加できます。")
	case "revision_conflict":
		writeError(w, 409, "別の画面でデータが更新されました。再取得してから保存してください。")
	case "grades_unavailable", "auth_unavailable":
		writeError(w, 503, "成績を処理できません。時間をおいて再試行してください。")
	default:
		writeError(w, 502, "成績サービスの応答を読み込めません。")
	}
}

// strictObjectは重複キー・未知キー・不足キーを拒否し、各値をそのまま返す。
func strictObject(data []byte, keys ...string) (map[string]json.RawMessage, bool) {
	decoder := json.NewDecoder(bytes.NewReader(data))
	if token, err := decoder.Token(); err != nil || token != json.Delim('{') {
		return nil, false
	}
	allowed := map[string]bool{}
	for _, key := range keys {
		allowed[key] = true
	}
	fields := map[string]json.RawMessage{}
	for decoder.More() {
		token, err := decoder.Token()
		key, ok := token.(string)
		if err != nil || !ok || !allowed[key] || fields[key] != nil {
			return nil, false
		}
		var value json.RawMessage
		if decoder.Decode(&value) != nil {
			return nil, false
		}
		fields[key] = value
	}
	if token, err := decoder.Token(); err != nil || token != json.Delim('}') || len(fields) != len(keys) {
		return nil, false
	}
	if _, err := decoder.Token(); err != io.EOF {
		return nil, false
	}
	return fields, true
}

func isNull(raw json.RawMessage) bool { return string(raw) == "null" }

func decodeString(raw json.RawMessage) (string, bool) {
	var value string
	return value, !isNull(raw) && json.Unmarshal(raw, &value) == nil
}

func decodeInt(raw json.RawMessage, minimum, maximum int64) (int64, bool) {
	var value int64
	return value, !isNull(raw) && json.Unmarshal(raw, &value) == nil && value >= minimum && value <= maximum
}

func decodeGradeSet(body []byte) (*application.GradeSet, string) {
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
	grades := make([]application.GradeAttempt, 0, len(items))
	for _, item := range items {
		grade, ok := decodeGradeAttempt(item)
		if !ok {
			return nil, gradeInputDetail
		}
		grades = append(grades, grade)
	}
	return &application.GradeSet{ExpectedRevision: revision, Grades: grades}, ""
}

func decodeGradeAttempt(item json.RawMessage) (application.GradeAttempt, bool) {
	var grade application.GradeAttempt
	fields, ok := strictObject(item, "course_id", "attempt_no", "result_status", "grade_code", "academic_year", "term_code")
	if !ok {
		return grade, false
	}
	courseID, ok := decodeString(fields["course_id"])
	if !ok {
		return grade, false
	}
	var err error
	if grade.CourseID, err = normalizeUUID(courseID); err != nil {
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
