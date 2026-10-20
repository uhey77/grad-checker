package schemas

import (
	"encoding/json"

	"net/url"
	"strconv"
	"strings"

	"grad-checker/backend/modules/requirements/application/ports"
)

const (
	ChecksPath       = "/api/checks"
	MaxCheckBody     = 16 << 10
	DefaultCheckPage = 20
	MaxCheckPage     = 100
	CheckNotFound    = "判定履歴が見つかりません。"
	CheckBodyDetail  = "判定の送信形式が不正です。expected_revisionと修了条件の回答を確認してください。"
	CheckPageDetail  = "履歴の表示範囲が不正です。limitは1〜100、offsetは0以上の整数で各1回まで指定してください。"
)

// parseCheckPageは一覧のlimit（既定20、1〜100）とoffset（既定0）を10進数の整数で受け付ける。
func ParseCheckPage(rawQuery string) (*ports.CheckPage, bool) {
	query, err := url.ParseQuery(rawQuery)
	if err != nil {
		return nil, false
	}
	page := &ports.CheckPage{Limit: DefaultCheckPage}
	for key, values := range query {
		if len(values) != 1 {
			return nil, false
		}
		var ok bool
		switch key {
		case "limit":
			page.Limit, ok = ParseDecimal(values[0], 1, MaxCheckPage)
		case "offset":
			page.Offset, ok = ParseDecimal(values[0], 0, MaxSafeRevision)
		}
		if !ok {
			return nil, false
		}
	}
	return page, true
}

// parseDecimalは符号・空白・小数を含まない10進数の整数だけを範囲内で受け付ける。
func ParseDecimal(value string, minimum, maximum int64) (int64, bool) {
	if value == "" || strings.Trim(value, "0123456789") != "" {
		return 0, false
	}
	number, err := strconv.ParseInt(value, 10, 64)
	return number, err == nil && number >= minimum && number <= maximum
}

func ParseCompletionAnswers(raw json.RawMessage) ([]ports.CompletionAnswer, bool) {
	if len(raw) == 0 {
		return nil, true
	}
	var rows []json.RawMessage
	if string(raw) == "null" || json.Unmarshal(raw, &rows) != nil || len(rows) > 50 {
		return nil, false
	}
	answers := []ports.CompletionAnswer{}
	seen := map[string]bool{}
	for _, row := range rows {
		fields, ok := StrictObject(row, "code", "status")
		if !ok || len(fields) != 2 {
			return nil, false
		}
		var code, status string
		if json.Unmarshal(fields["code"], &code) != nil || json.Unmarshal(fields["status"], &status) != nil || len(code) == 0 || len(code) > 100 || seen[code] || (status != "met" && status != "not_met" && status != "unknown") {
			return nil, false
		}
		seen[code] = true
		answers = append(answers, ports.CompletionAnswer{Code: code, Status: status})
	}
	return answers, true
}
