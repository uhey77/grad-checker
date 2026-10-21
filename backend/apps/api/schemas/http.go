package schemas

import (
	"bytes"
	"encoding/hex"
	"encoding/json"
	"errors"
	"io"

	"net/http"

	"strings"
)

// JavaScriptの整数で安全に扱える更新版の上限。
const MaxSafeRevision = 9007199254740990

func WriteJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.Header().Set("Cache-Control", "no-store")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}

func WriteError(w http.ResponseWriter, status int, detail string) {
	WriteJSON(w, status, map[string]string{"detail": detail})
}

// 従来のPythonのUUIDコンストラクターが受け付けていた表記を標準形へ揃える。
func NormalizeUUID(value string) (string, error) {
	value = strings.ReplaceAll(strings.ReplaceAll(value, "urn:", ""), "uuid:", "")
	value = strings.ReplaceAll(strings.Trim(value, "{}"), "-", "")
	if len(value) != 32 {
		return "", errors.New("invalid UUID")
	}
	if _, err := hex.DecodeString(value); err != nil {
		return "", err
	}
	value = strings.ToLower(value)
	return value[:8] + "-" + value[8:12] + "-" + value[12:16] + "-" + value[16:20] + "-" + value[20:], nil
}

// strictObjectは重複キー・未知キー・不足キーを拒否し、各値をそのまま返す。
func StrictObject(data []byte, keys ...string) (map[string]json.RawMessage, bool) {
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

func IsNull(raw json.RawMessage) bool { return string(raw) == "null" }

func DecodeString(raw json.RawMessage) (string, bool) {
	var value string
	return value, !IsNull(raw) && json.Unmarshal(raw, &value) == nil
}

func DecodeInt(raw json.RawMessage, minimum, maximum int64) (int64, bool) {
	var value int64
	return value, !IsNull(raw) && json.Unmarshal(raw, &value) == nil && value >= minimum && value <= maximum
}

func DecodeUUID(raw json.RawMessage) (string, bool) {
	value, ok := DecodeString(raw)
	if !ok {
		return "", false
	}
	id, err := NormalizeUUID(value)
	return id, err == nil
}
